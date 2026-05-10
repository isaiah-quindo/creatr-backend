from collections import Counter

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from embeds.services import fetch_embed_data

from .models import CreatorProfile, CustomLink, PortfolioItem, SocialAccount
from .serializers import (
    CreatorProfileSerializer,
    CustomLinkSerializer,
    PortfolioItemSerializer,
    PublicCreatorSerializer,
    ReorderSerializer,
    SocialAccountSerializer,
    ThemeSerializer,
)


User = get_user_model()


class MyCreatorProfileView(APIView):
    """GET / PUT the current user's CreatorProfile (niches, theme, links, rates)."""
    permission_classes = [IsAuthenticated]

    def _get_profile(self, user) -> CreatorProfile:
        # The post_save signal creates this, but get_or_create keeps it idempotent
        # for any users that pre-date the signal.
        profile, _ = CreatorProfile.objects.get_or_create(user=user)
        return profile

    def get(self, request):
        return Response(CreatorProfileSerializer(self._get_profile(request.user)).data)

    def put(self, request):
        serializer = CreatorProfileSerializer(
            self._get_profile(request.user), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MyThemeView(APIView):
    """PUT-only endpoint for the theme picker — keeps the dashboard call small."""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        profile, _ = CreatorProfile.objects.get_or_create(user=request.user)
        serializer = ThemeSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MySocialAccountsViewSet(viewsets.ModelViewSet):
    """CRUD for the current user's social accounts (/api/me/socials/)."""
    serializer_class = SocialAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SocialAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # New socials append to the bottom of the list unless the client set
        # an explicit sort_order — keeps "add social" feeling like an append.
        if "sort_order" not in serializer.validated_data:
            tail = self.get_queryset().count()
            serializer.save(user=self.request.user, sort_order=tail)
        else:
            serializer.save(user=self.request.user)

    @action(detail=False, methods=["put"], url_path="reorder", url_name="reorder")
    def reorder(self, request):
        """Apply a new sort order. Body: {"ids": [3, 1, 2]} — first id ranks 0."""
        return _apply_reorder(
            request,
            queryset=self.get_queryset(),
            model=SocialAccount,
            serializer_class=SocialAccountSerializer,
        )


class MyPortfolioViewSet(viewsets.ModelViewSet):
    """CRUD for the current user's portfolio items (/api/me/portfolio/).

    When `media_type=video_embed` and an `original_url` is provided, we hit
    the relevant oEmbed endpoint and persist the embed HTML, thumbnail, title,
    and detected platform alongside the row.
    """
    serializer_class = PortfolioItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PortfolioItem.objects.filter(user=self.request.user)

    def _embed_fields(self, validated: dict) -> dict:
        """Resolve the embed fields for a video URL, or return empties."""
        if validated.get("media_type") != "video_embed":
            return {}
        url = validated.get("original_url")
        if not url:
            return {}
        data = fetch_embed_data(url)
        return {
            "platform_source": data["platform"],
            "embed_html": data["embed_html"],
            "thumbnail_url": data["thumbnail_url"],
            "video_title": data["video_title"],
        }

    def perform_create(self, serializer):
        extra = self._embed_fields(serializer.validated_data)
        serializer.save(user=self.request.user, **extra)

    def perform_update(self, serializer):
        # Re-fetch embed data only when the URL changed; otherwise leave
        # the persisted oEmbed payload alone.
        instance = serializer.instance
        new_url = serializer.validated_data.get("original_url", instance.original_url)
        new_type = serializer.validated_data.get("media_type", instance.media_type)
        url_changed = new_url and new_url != instance.original_url
        type_changed = new_type != instance.media_type

        if url_changed or (type_changed and new_type == "video_embed"):
            payload = {**serializer.validated_data, "media_type": new_type, "original_url": new_url}
            extra = self._embed_fields(payload)
            serializer.save(**extra)
        else:
            serializer.save()

    @action(detail=False, methods=["put"], url_path="reorder", url_name="reorder")
    def reorder(self, request):
        """Apply a new sort order. Body: {"ids": [3, 1, 2]} — first id ranks 0."""
        return _apply_reorder(
            request,
            queryset=self.get_queryset(),
            model=PortfolioItem,
            serializer_class=PortfolioItemSerializer,
        )


class MyCustomLinksViewSet(viewsets.ModelViewSet):
    """CRUD for the current user's custom links (/api/me/links/)."""
    serializer_class = CustomLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CustomLink.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # New links land at the bottom of the list unless the client explicitly
        # set a sort_order — keeps "add link" feeling like an append.
        if "sort_order" not in serializer.validated_data:
            tail = self.get_queryset().count()
            serializer.save(user=self.request.user, sort_order=tail)
        else:
            serializer.save(user=self.request.user)

    @action(detail=False, methods=["put"], url_path="reorder", url_name="reorder")
    def reorder(self, request):
        """Apply a new sort order. Body: {"ids": [3, 1, 2]} — first id ranks 0."""
        return _apply_reorder(
            request,
            queryset=self.get_queryset(),
            model=CustomLink,
            serializer_class=CustomLinkSerializer,
        )


def _apply_reorder(request, *, queryset, model, serializer_class):
    """Shared reorder handler for portfolio + custom links.

    Validates `{ids: [...]}`, ensures every id belongs to the caller, then
    rewrites `sort_order` in a single transaction.
    """
    serializer = ReorderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ids = serializer.validated_data["ids"]

    owned = set(queryset.filter(pk__in=ids).values_list("pk", flat=True))
    unknown = [i for i in ids if i not in owned]
    if unknown:
        return Response(
            {"detail": f"Items not found or not yours: {unknown}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        for index, pk in enumerate(ids):
            model.objects.filter(pk=pk, user=request.user).update(sort_order=index)

    return Response(serializer_class(queryset, many=True).data)


class PublicNichesView(APIView):
    """GET /api/niches/ — popular niches across public creators.

    Powers the niches autocomplete on the profile editor. Returns a flat list
    of niche labels sorted by frequency (most-used first), then alphabetically.
    Public so the editor can fetch suggestions without bouncing through auth.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        rows = CreatorProfile.objects.filter(is_public=True).values_list(
            "niches", flat=True
        )
        counter: Counter[str] = Counter()
        for niches in rows:
            for raw in niches or []:
                label = (raw or "").strip()
                if label:
                    counter[label] += 1
        ordered = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0].lower()))
        return Response({"niches": [label for label, _ in ordered]})


class PublicCreatorView(APIView):
    """GET /api/creators/<username>/ — public link-in-bio payload.

    Looks up the user by case-insensitive username, requires the creator to
    have flipped `is_public` on, and returns the full bundle the public page
    needs in one round trip.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # never read session cookies on public reads

    def get(self, request, username: str):
        # Tolerate the leading "@" so the API mirrors the URL shape.
        username = username.lstrip("@")
        user = get_object_or_404(
            User.objects.select_related("creator_profile"),
            username__iexact=username,
        )
        profile, _ = CreatorProfile.objects.get_or_create(user=user)
        if not profile.is_public:
            return Response(
                {"detail": "This profile is not public."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "location": user.location,
            "niches": profile.niches,
            "theme": profile.theme,
            "rate_card": profile.rate_card,
            "socials": user.social_accounts.all(),
            "portfolio": user.portfolio_items.all(),
            "custom_links": user.custom_links.all(),
        }
        return Response(PublicCreatorSerializer(payload).data)
