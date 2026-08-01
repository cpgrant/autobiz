from django.contrib import admin

from .models import (
    ActionProposal,
    Approval,
    AuditEvent,
    Company,
    Customer,
    CustomerRequest,
    Deliverable,
    Engagement,
    FinancialEntry,
    Goal,
    Metric,
    Offer,
    OperatingCycle,
    Opportunity,
    Product,
    Risk,
    SyntheticPayment,
    WeeklyReport,
    WorkflowRun,
    WorkItem,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "is_synthetic", "external_execution_enabled", "updated_at")
    search_fields = ("name", "key")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "is_synthetic", "primary_email", "updated_at")
    list_filter = ("status", "is_synthetic")
    search_fields = ("name", "primary_email")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "status", "is_synthetic", "updated_at")
    list_filter = ("status", "is_synthetic")
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


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "current_value", "target_value", "unit")
    list_filter = ("status", "is_synthetic")


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("customer", "product", "stage", "estimated_value_eur", "is_synthetic")
    list_filter = ("stage", "product", "is_synthetic")


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ("title", "function", "priority", "status", "requires_approval")
    list_filter = ("function", "status", "requires_approval")


@admin.register(FinancialEntry)
class FinancialEntryAdmin(admin.ModelAdmin):
    list_display = ("description", "entry_type", "amount_eur", "occurred_on", "is_synthetic")
    list_filter = ("entry_type", "is_synthetic")


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = ("title", "severity", "status", "is_synthetic")
    list_filter = ("severity", "status")


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ("name", "value", "target_value", "unit", "is_synthetic")


@admin.register(OperatingCycle)
class OperatingCycleAdmin(admin.ModelAdmin):
    list_display = ("company", "operating_date", "status", "is_synthetic")
    list_filter = ("status",)


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ("company", "week_start", "cycle_count", "is_synthetic", "updated_at")
    list_filter = ("is_synthetic",)


@admin.register(ActionProposal)
class ActionProposalAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "action_type",
        "authority_level",
        "status",
        "requires_approval",
        "executor_available",
    )
    list_filter = ("authority_level", "status", "requires_approval", "is_external")


@admin.register(CustomerRequest)
class CustomerRequestAdmin(admin.ModelAdmin):
    list_display = ("customer", "product", "status", "is_synthetic", "created_at")
    list_filter = ("status", "product", "is_synthetic")
    search_fields = ("customer__name", "request_text", "desired_outcome")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("title", "customer_request", "price_eur", "status", "is_synthetic")
    list_filter = ("status", "is_synthetic")


@admin.register(SyntheticPayment)
class SyntheticPaymentAdmin(admin.ModelAdmin):
    list_display = ("offer", "amount_eur", "status", "provider", "paid_at")
    list_filter = ("status", "provider", "is_synthetic")
    readonly_fields = ("offer", "amount_eur", "status", "paid_at", "provider", "external_reference")

    def has_add_permission(self, request):
        return False


@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "customer_request",
        "version",
        "is_current",
        "status",
        "is_synthetic",
        "updated_at",
    )
    list_filter = ("status", "is_current", "is_synthetic")
