from django.urls import path

from . import views


urlpatterns = [
    path(
        "<str:username>/",
        views.PublicCreatorView.as_view(),
        name="public-creator",
    ),
]
