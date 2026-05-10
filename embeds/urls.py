from django.urls import path

from . import views


urlpatterns = [
    path("preview/", views.EmbedPreviewView.as_view(), name="embed-preview"),
]
