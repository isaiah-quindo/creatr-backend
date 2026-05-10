from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.supabase import upload_file

from .emails import send_verification_email
from .models import EmailVerificationToken
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

User = get_user_model()

AVATAR_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class CsrfView(APIView):
    """GET to set the csrftoken cookie before any unsafe request from the SPA."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
            verification = EmailVerificationToken.issue(user)
        send_verification_email(user, verification.token)
        return Response(
            {
                "email": user.email,
                "email_verified": False,
                "detail": "Account created. Check your email for a verification link.",
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if not user.email_verified:
            return Response(
                {
                    "detail": "Please verify your email before signing in.",
                    "code": "email_not_verified",
                    "email": user.email,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        login(request, user)
        return Response(UserSerializer(user).data)


class VerifyEmailView(APIView):
    """Confirm an emailed token. On success, mark verified and log the user in."""

    permission_classes = [AllowAny]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if not token:
            raise ValidationError({"token": "Missing token."})

        try:
            record = EmailVerificationToken.objects.select_related("user").get(token=token)
        except EmailVerificationToken.DoesNotExist:
            raise ValidationError({"token": "Invalid or expired link."})

        if not record.is_valid():
            raise ValidationError({"token": "This link has expired or already been used."})

        with transaction.atomic():
            record.consume()
            user = record.user
            if not user.email_verified:
                user.email_verified = True
                user.email_verified_at = timezone.now()
                user.save(update_fields=["email_verified", "email_verified_at"])

        login(request, user, backend="accounts.auth_backends.EmailBackend")
        return Response(UserSerializer(user).data)


class ResendVerificationView(APIView):
    """Issue a fresh verification token for an unverified account."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        if not email:
            raise ValidationError({"email": "Missing email."})

        # Don't reveal whether the email exists — always return the same response.
        user = User.objects.filter(email__iexact=email).first()
        if user is not None and not user.email_verified:
            verification = EmailVerificationToken.issue(user)
            send_verification_email(user, verification.token)

        return Response(
            {"detail": "If that email matches an unverified account, a new link is on its way."}
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class GoogleLoginView(APIView):
    """Exchange a Google ID token (from Google Identity Services) for a Django session.

    Frontend posts {"credential": "<id_token>"} — the JWT credential Google returns
    in its `CredentialResponse` callback. We verify it with Google's public keys,
    then find-or-create a User by verified email and log them in.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.GOOGLE_CLIENT_ID:
            raise ValidationError({"credential": "Google sign-in is not configured."})

        credential = request.data.get("credential")
        if not credential:
            raise ValidationError({"credential": "Missing Google credential."})

        try:
            payload = google_id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError:
            raise ValidationError({"credential": "Invalid Google credential."})

        if not payload.get("email_verified"):
            raise ValidationError({"credential": "Google account email is not verified."})

        email = payload.get("email")
        if not email:
            raise ValidationError({"credential": "Google credential did not include an email."})

        with transaction.atomic():
            user = User.objects.filter(email__iexact=email).first()
            if user is None:
                user = User(
                    email=email,
                    first_name=payload.get("given_name", "")[:150],
                    last_name=payload.get("family_name", "")[:150],
                    avatar_url=payload.get("picture", "")[:500],
                    email_verified=True,
                    email_verified_at=timezone.now(),
                )
                user.set_unusable_password()
                user.save()
            elif not user.email_verified:
                # Google already confirmed the address — skip our own email step.
                user.email_verified = True
                user.email_verified_at = timezone.now()
                user.save(update_fields=["email_verified", "email_verified_at"])

        login(request, user, backend="accounts.auth_backends.EmailBackend")
        return Response(UserSerializer(user).data)


class MeView(APIView):
    """GET / PUT the current user's basic profile fields (not creator-specific)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AvatarUploadView(APIView):
    """POST a multipart `file` field; uploads to Supabase Storage and sets `avatar_url`."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "No file provided."})

        if upload.size > AVATAR_MAX_BYTES:
            raise ValidationError({"file": "Image must be under 5 MB."})

        content_type = (upload.content_type or "").lower()
        if content_type not in AVATAR_ALLOWED_TYPES:
            raise ValidationError({"file": "Use a JPEG, PNG, WebP, or GIF image."})

        public_url = upload_file(
            upload,
            folder=f"avatars/{request.user.id}",
            filename=upload.name,
            content_type=content_type,
        )

        request.user.avatar_url = public_url
        request.user.save(update_fields=["avatar_url"])
        return Response(UserSerializer(request.user).data)
