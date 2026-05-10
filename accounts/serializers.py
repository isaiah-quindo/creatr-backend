from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public-facing user fields. Pairs with CreatorProfileSerializer in /api/me/."""

    username = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=False,
        max_length=30,
    )
    bio = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=180,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "avatar_url",
            "bio",
            "location",
            "is_creator",
            "email_verified",
        ]
        read_only_fields = ["id", "is_creator", "email_verified"]

    def validate_username(self, value):
        if value is None:
            return None
        from .models import RESERVED_USERNAMES, username_validator
        username_validator(value)
        if value.lower() in RESERVED_USERNAMES:
            raise serializers.ValidationError("That username is reserved.")
        qs = User.objects.filter(username__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("That username is taken.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ["email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid credentials.")
        attrs["user"] = user
        return attrs
