from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r"socials", views.MySocialAccountsViewSet, basename="my-socials")
router.register(r"portfolio", views.MyPortfolioViewSet, basename="my-portfolio")
router.register(r"links", views.MyCustomLinksViewSet, basename="my-links")


urlpatterns = [
    path("profile/", views.MyCreatorProfileView.as_view(), name="my-profile"),
    path("theme/", views.MyThemeView.as_view(), name="my-theme"),
    path("", include(router.urls)),
]
