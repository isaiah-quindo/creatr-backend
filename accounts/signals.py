from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_creator_profile(sender, instance, created, **kwargs):
    """Every new User gets a CreatorProfile so /api/me/ always has one to return."""
    if not created:
        return
    from creators.models import CreatorProfile
    CreatorProfile.objects.get_or_create(user=instance)
