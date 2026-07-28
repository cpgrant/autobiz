from django.contrib import admin

from .models import Approval, AuditEvent, Customer, Engagement, Product, WorkflowRun


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "primary_email", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "primary_email")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "key")


@admin.register(Engagement)
class EngagementAdmin(admin.ModelAdmin):
    list_display = ("customer", "product", "status", "starts_on", "ends_on")
    list_filter = ("status", "product")
    search_fields = ("customer__name", "product__name")


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = ("workflow_key", "engagement", "status", "attempt_count", "created_at")
    list_filter = ("status", "workflow_key")
    search_fields = ("workflow_key", "engagement__customer__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ("action_type", "workflow_run", "status", "decided_by", "created_at")
    list_filter = ("status", "action_type")
    search_fields = ("action_type", "workflow_run__workflow_key")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "actor", "workflow_run", "created_at")
    list_filter = ("event_type",)
    search_fields = ("event_type", "actor")
    readonly_fields = ("workflow_run", "event_type", "actor", "payload", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
