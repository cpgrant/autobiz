from django.contrib import admin
from django.urls import path

from apps.operations.views import health, readiness

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("ready/", readiness, name="readiness"),
]
