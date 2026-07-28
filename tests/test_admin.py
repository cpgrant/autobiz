import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.operations.admin import AuditEventAdmin
from apps.operations.models import AuditEvent


@pytest.mark.django_db
def test_audit_admin_is_read_only(operator):
    request = RequestFactory().get("/admin/")
    request.user = operator
    model_admin = AuditEventAdmin(AuditEvent, admin.site)

    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_change_permission(request) is False
    assert model_admin.has_delete_permission(request) is False
