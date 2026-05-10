from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import EmailVerificationToken, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "username", "email_verified", "is_staff", "date_joined")
    list_filter = ("email_verified", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("email_verified_at", "last_login", "date_joined")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Verification", {"fields": ("email_verified", "email_verified_at")}),
        ("Creator", {"fields": ("avatar_url", "bio", "location", "is_creator")}),
    )


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "used_at")
    search_fields = ("user__email", "token")
    readonly_fields = ("token", "created_at", "expires_at", "used_at", "user")
    ordering = ("-created_at",)
