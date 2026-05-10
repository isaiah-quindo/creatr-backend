from django.urls import path

from . import views


urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/google/", views.GoogleLoginView.as_view(), name="auth-google"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/verify-email/", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path("auth/resend-verification/", views.ResendVerificationView.as_view(), name="auth-resend-verification"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/avatar/", views.AvatarUploadView.as_view(), name="me-avatar"),
]
