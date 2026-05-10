from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_user_email_alter_user_username"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="avatar_url",
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
