from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


THEME_CHOICES = [
    ("clean", "Clean"),
    ("bold", "Bold"),
    ("warm", "Warm"),
    ("midnight", "Midnight"),
    ("cover", "Cover"),
    ("indigo", "Indigo"),
    ("honey", "Honey"),
    ("azure", "Azure"),
]

PLATFORM_CHOICES = [
    ("tiktok", "TikTok"),
    ("instagram", "Instagram"),
    ("youtube", "YouTube"),
    ("facebook", "Facebook"),
]

MEDIA_TYPE_CHOICES = [
    ("video_embed", "Video embed"),
    ("video_upload", "Video upload"),
    ("image", "Image"),
]


class CreatorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="creator_profile",
    )
    niches = ArrayField(
        models.CharField(max_length=40),
        default=list,
        blank=True,
        help_text='e.g. ["beauty", "food", "tech"]',
    )
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default="clean")
    is_public = models.BooleanField(default=False)
    rate_card = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"deliverables": [{"type": ..., "rate": ..., "notes": ...}]}',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"CreatorProfile(@{self.user.username})"


class CustomLink(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="custom_links",
    )
    title = models.CharField(max_length=100)
    url = models.URLField()
    icon = models.CharField(max_length=50, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"CustomLink({self.title})"


class SocialAccount(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    handle = models.CharField(max_length=100)
    profile_url = models.URLField()
    followers = models.PositiveIntegerField(default=0)
    avg_views = models.PositiveIntegerField(default=0)
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("user", "platform", "handle")]
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.platform}:@{self.handle}"


class PortfolioItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio_items",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES)
    # For video_embed: original URL pasted by creator (TikTok / YouTube / Instagram).
    # 500 chars to fit signed/query-heavy URLs (TikTok, IG reels, etc).
    original_url = models.URLField(max_length=500, blank=True)
    # For video_upload / image: Supabase Storage public URL
    media_url = models.URLField(max_length=500, blank=True)
    platform_source = models.CharField(
        max_length=20, choices=PLATFORM_CHOICES, blank=True
    )
    embed_html = models.TextField(blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    video_title = models.CharField(max_length=300, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]

    def __str__(self) -> str:
        return f"PortfolioItem({self.title})"
