import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_links_to_table(apps, schema_editor):
    CreatorProfile = apps.get_model("creators", "CreatorProfile")
    CustomLink = apps.get_model("creators", "CustomLink")
    for profile in CreatorProfile.objects.all():
        links = profile.custom_links or []
        for index, link in enumerate(links):
            if not isinstance(link, dict):
                continue
            url = (link.get("url") or "").strip()
            if not url:
                continue
            CustomLink.objects.create(
                user_id=profile.user_id,
                title=(link.get("title") or "").strip()[:100] or url,
                url=url,
                icon=(link.get("icon") or "").strip()[:50],
                sort_order=index,
            )


def copy_links_to_jsonfield(apps, schema_editor):
    CreatorProfile = apps.get_model("creators", "CreatorProfile")
    CustomLink = apps.get_model("creators", "CustomLink")
    for profile in CreatorProfile.objects.all():
        rows = (
            CustomLink.objects.filter(user_id=profile.user_id)
            .order_by("sort_order", "id")
            .values("title", "url", "icon")
        )
        profile.custom_links = list(rows)
        profile.save(update_fields=["custom_links"])


class Migration(migrations.Migration):

    dependencies = [
        ("creators", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100)),
                ("url", models.URLField()),
                ("icon", models.CharField(blank=True, max_length=50)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="custom_links",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.RunPython(copy_links_to_table, copy_links_to_jsonfield),
        migrations.RemoveField(model_name="creatorprofile", name="custom_links"),
    ]
