from django.contrib import admin
from django.urls import include, path

from creators.views import PublicNichesView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/me/", include("creators.urls")),
    path("api/niches/", PublicNichesView.as_view(), name="public-niches"),
    path("api/creators/", include("creators.public_urls")),
    path("api/embed/", include("embeds.urls")),
]
