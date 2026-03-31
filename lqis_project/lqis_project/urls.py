from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("users/", include("users.urls")),
    path("sampling/", include("sampling.urls")),
    path("ai/", include("ai_engine.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("reporting/", include("reporting.urls")),
]

# Always serve media files - required for local disk fallback when Cloudinary is not configured.
# When Cloudinary IS configured, it returns absolute URLs so this route is harmlessly bypassed.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
