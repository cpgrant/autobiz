from django.contrib import admin
from django.urls import path

from apps.operations.views import company_status, health, home, readiness

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("company/", company_status, name="company-status"),
    path("health/", health, name="health"),
    path("ready/", readiness, name="readiness"),
]
