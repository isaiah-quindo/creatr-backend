from rest_framework import serializers

from .models import CreatorProfile, CustomLink, PortfolioItem, SocialAccount


class CreatorProfileSerializer(serializers.ModelSerializer):
    niches = serializers.ListField(
        child=serializers.CharField(),
        max_length=3,
        required=False,
    )

    class Meta:
        model = CreatorProfile
        fields = [
            "niches",
            "theme",
            "is_public",
            "rate_card",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorProfile
        fields = ["theme"]


class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = [
            "id",
            "platform",
            "handle",
            "profile_url",
            "followers",
            "avg_views",
            "engagement_rate",
        ]
        read_only_fields = ["id"]


class PortfolioItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioItem
        fields = [
            "id",
            "title",
            "description",
            "media_type",
            "original_url",
            "media_url",
            "platform_source",
            "embed_html",
            "thumbnail_url",
            "video_title",
            "sort_order",
            "created_at",
        ]
        # Embed fields are populated server-side from oEmbed; clients can't override.
        read_only_fields = [
            "id",
            "platform_source",
            "embed_html",
            "thumbnail_url",
            "video_title",
            "created_at",
        ]


class CustomLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomLink
        fields = ["id", "title", "url", "icon", "sort_order", "created_at"]
        read_only_fields = ["id", "created_at"]


class ReorderSerializer(serializers.Serializer):
    """Shared body shape for reorder endpoints — `{ids: [int, ...]}`."""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class PublicCreatorSerializer(serializers.Serializer):
    """Composite payload for the public /@username page.

    Bundles user fields, creator profile, social accounts, and portfolio so
    the page can render in a single request without a waterfall.
    """

    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    avatar_url = serializers.URLField()
    bio = serializers.CharField()
    location = serializers.CharField()

    niches = serializers.ListField(child=serializers.CharField())
    theme = serializers.CharField()
    rate_card = serializers.JSONField()

    socials = SocialAccountSerializer(many=True)
    portfolio = PortfolioItemSerializer(many=True)
    custom_links = CustomLinkSerializer(many=True)
