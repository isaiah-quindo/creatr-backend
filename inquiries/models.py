from django.conf import settings
from django.db import models


STATUS_CHOICES = [
    ("new", "New"),
    ("read", "Read"),
    ("replied", "Replied"),
]


class Inquiry(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inquiries",
    )
    sender_name = models.CharField(max_length=100)
    sender_email = models.EmailField()
    message = models.TextField()
    budget_range = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["creator", "status"])]

    def __str__(self) -> str:
        return f"Inquiry from {self.sender_name} -> @{self.creator.username}"
