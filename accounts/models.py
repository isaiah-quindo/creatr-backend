import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


username_validator = RegexValidator(
    regex=r"^[a-z0-9_.]+$",
    message="Username may only contain lowercase letters, digits, underscores, and dots.",
)

RESERVED_USERNAMES = frozenset({
    "admin",
    "support",
    "official",
    "creatr",
})


class User(AbstractUser):
    username = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        validators=[username_validator],
        help_text="Lowercase letters, digits, underscores, and dots. Used in /@username URLs.",
    )
    email = models.EmailField(unique=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    is_creator = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"@{self.username}" if self.username else self.email

    def mark_email_verified(self) -> None:
        self.email_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=["email_verified", "email_verified_at"])


def _default_token_expiry():
    hours = getattr(settings, "EMAIL_VERIFICATION_TOKEN_HOURS", 24)
    return timezone.now() + timedelta(hours=hours)


class EmailVerificationToken(models.Model):
    """Single-use, expiring token mailed to a user to confirm their email."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField(default=_default_token_expiry)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def issue(cls, user) -> "EmailVerificationToken":
        cls.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        return cls.objects.create(user=user, token=secrets.token_urlsafe(32))

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    def consume(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])
