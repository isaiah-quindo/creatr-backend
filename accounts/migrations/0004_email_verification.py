from django.conf import settings
from django.db import migrations, models
from django.utils import timezone

import accounts.models


def grandfather_existing_users(apps, schema_editor):
    """
    Treat any user who existed before this migration as already-verified.
    Without this, the verification gate would lock out every account that
    signed up during Phase 1/2.
    """
    User = apps.get_model("accounts", "User")
    now = timezone.now()
    User.objects.filter(email_verified=False).update(
        email_verified=True,
        email_verified_at=now,
    )


def noop_reverse(apps, schema_editor):
    """No-op — reversing the migration drops the columns anyway."""


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_user_avatar_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='email_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='EmailVerificationToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=64, unique=True)),
                ('expires_at', models.DateTimeField(default=accounts.models._default_token_expiry)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='email_verification_tokens',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.RunPython(grandfather_existing_users, noop_reverse),
    ]
