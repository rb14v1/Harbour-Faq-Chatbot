from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.auth_urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/faqs/", include("apps.faqs.faq_urls")),
    path("api/", include("apps.faqs.urls")),
]
