import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    mission = models.TextField()
    is_synthetic = models.BooleanField(default=True)
    external_execution_enabled = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "companies"

    def __str__(self) -> str:
        return self.name


class Customer(TimestampedModel):
    class Status(models.TextChoices):
        PROSPECT = "prospect", "Prospect"
        PILOT = "pilot", "Pilot"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="customers", null=True, blank=True
    )
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status, default=Status.PROSPECT)
    primary_email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    is_synthetic = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(TimestampedModel):
    class Status(models.TextChoices):
        HYPOTHESIS = "hypothesis", "Hypothesis"
        PILOT = "pilot", "Pilot"
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="products", null=True, blank=True
    )
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status, default=Status.HYPOTHESIS)
    promised_outcome = models.TextField()
    is_synthetic = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Engagement(TimestampedModel):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        PILOT = "pilot", "Pilot"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ENDED = "ended", "Ended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="engagements")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="engagements")
    status = models.CharField(max_length=20, choices=Status, default=Status.PROPOSED)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    is_synthetic = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.customer} — {self.product}"


class Goal(TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ACHIEVED = "achieved", "Achieved"
        PAUSED = "paused", "Paused"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="goals")
    key = models.SlugField()
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status, default=Status.ACTIVE)
    target_value = models.DecimalField(max_digits=12, decimal_places=2)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=40)
    due_on = models.DateField(null=True, blank=True)
    is_synthetic = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "key"], name="unique_goal_key")]

    def __str__(self) -> str:
        return self.name


class Opportunity(TimestampedModel):
    class Stage(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        QUALIFIED = "qualified", "Qualified"
        PROPOSED = "proposed", "Proposed"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="opportunities")
    key = models.SlugField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="opportunities")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="opportunities")
    stage = models.CharField(max_length=20, choices=Stage, default=Stage.DISCOVERED)
    estimated_value_eur = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    probability_percent = models.PositiveSmallIntegerField(default=0)
    is_synthetic = models.BooleanField(default=True)

    class Meta:
        ordering = ["-estimated_value_eur"]
        constraints = [
            models.UniqueConstraint(fields=["company", "key"], name="unique_opportunity_key")
        ]

    def __str__(self) -> str:
        return f"{self.customer} — {self.product}"


class WorkItem(TimestampedModel):
    class Function(models.TextChoices):
        DIRECTION = "direction", "Direction"
        GROWTH = "growth", "Growth"
        DELIVERY = "delivery", "Delivery"
        FINANCE = "finance", "Finance"
        OPERATIONS = "operations", "Operations"

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        READY = "ready", "Ready"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        DONE = "done", "Done"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="work_items")
    engagement = models.ForeignKey(
        Engagement,
        on_delete=models.PROTECT,
        related_name="work_items",
        null=True,
        blank=True,
    )
    key = models.SlugField()
    title = models.CharField(max_length=240)
    function = models.CharField(max_length=20, choices=Function)
    status = models.CharField(max_length=20, choices=Status, default=Status.PROPOSED)
    priority = models.PositiveSmallIntegerField(default=3)
    requires_approval = models.BooleanField(default=False)
    is_synthetic = models.BooleanField(default=True)

    class Meta:
        ordering = ["priority", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "key"], name="unique_work_item_key")
        ]

    def __str__(self) -> str:
        return self.title


class FinancialEntry(TimestampedModel):
    class EntryType(models.TextChoices):
        REVENUE = "revenue", "Revenue"
        COST = "cost", "Cost"
        CASH = "cash", "Cash"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="financial_entries")
    key = models.SlugField()
    entry_type = models.CharField(max_length=20, choices=EntryType)
    description = models.CharField(max_length=240)
    amount_eur = models.DecimalField(max_digits=12, decimal_places=2)
    occurred_on = models.DateField()
    is_synthetic = models.BooleanField(default=True)

    class Meta:
        ordering = ["-occurred_on"]
        constraints = [
            models.UniqueConstraint(fields=["company", "key"], name="unique_financial_entry_key")
        ]

    def __str__(self) -> str:
        return self.description


class Risk(TimestampedModel):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MITIGATED = "mitigated", "Mitigated"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="risks")
    key = models.SlugField()
    title = models.CharField(max_length=240)
    severity = models.CharField(max_length=20, choices=Severity)
    status = models.CharField(max_length=20, choices=Status, default=Status.OPEN)
    mitigation = models.TextField(blank=True)
    is_synthetic = models.BooleanField(default=True)

    class Meta:
        ordering = ["status", "-severity"]
        constraints = [models.UniqueConstraint(fields=["company", "key"], name="unique_risk_key")]

    def __str__(self) -> str:
        return self.title


class Metric(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="metrics")
    key = models.SlugField()
    name = models.CharField(max_length=200)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=40)
    is_synthetic = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "key"], name="unique_metric_key")]

    def __str__(self) -> str:
        return self.name


class OperatingCycle(TimestampedModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="operating_cycles")
    operating_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status, default=Status.PLANNED)
    report = models.TextField(blank=True)
    is_synthetic = models.BooleanField(default=True)

    class Meta:
        ordering = ["-operating_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "operating_date"], name="unique_company_operating_date"
            )
        ]

    def __str__(self) -> str:
        return f"{self.company} — {self.operating_date}"


class ActionProposal(TimestampedModel):
    class AuthorityLevel(models.IntegerChoices):
        OBSERVE = 0, "Observe"
        DRAFT = 1, "Draft"
        BOUNDED_EXECUTE = 2, "Bounded execute"
        HUMAN_APPROVAL = 3, "Human approval"
        PROHIBITED = 4, "Prohibited"

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting approval"
        AUTHORIZED = "authorized", "Authorized"
        SIMULATED = "simulated", "Simulated"
        REJECTED = "rejected", "Rejected"
        BLOCKED = "blocked", "Blocked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="action_proposals")
    key = models.SlugField()
    operating_cycle = models.ForeignKey(
        OperatingCycle,
        on_delete=models.PROTECT,
        related_name="action_proposals",
        null=True,
        blank=True,
    )
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.PROTECT, related_name="action_proposals", null=True, blank=True
    )
    approval = models.OneToOneField(
        "Approval", on_delete=models.PROTECT, related_name="action_proposal", null=True, blank=True
    )
    action_type = models.SlugField()
    title = models.CharField(max_length=240)
    authority_level = models.PositiveSmallIntegerField(choices=AuthorityLevel)
    status = models.CharField(max_length=30, choices=Status, default=Status.PROPOSED)
    requires_approval = models.BooleanField(default=False)
    is_external = models.BooleanField(default=False)
    executor_available = models.BooleanField(default=False)
    outcome = models.JSONField(default=dict, blank=True)
    is_synthetic = models.BooleanField(default=True)

    class Meta:
        ordering = ["authority_level", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "key"], name="unique_action_proposal_key")
        ]

    def __str__(self) -> str:
        return self.title


class CustomerRequest(TimestampedModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        OFFERED = "offered", "Offer ready"
        ACCEPTED = "accepted", "Offer accepted"
        PAID = "paid", "Synthetic payment recorded"
        IN_DELIVERY = "in_delivery", "In delivery"
        DELIVERED = "delivered", "Delivered"
        REVISION_REQUESTED = "revision_requested", "Revision requested"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="customer_requests")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="requests")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="customer_requests")
    engagement = models.OneToOneField(
        Engagement,
        on_delete=models.PROTECT,
        related_name="customer_request",
        null=True,
        blank=True,
    )
    request_text = models.TextField()
    desired_outcome = models.TextField()
    status = models.CharField(max_length=30, choices=Status, default=Status.SUBMITTED)
    is_synthetic = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.customer} — {self.product} request"


class Offer(TimestampedModel):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        ACCEPTED = "accepted", "Accepted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_request = models.OneToOneField(
        CustomerRequest, on_delete=models.PROTECT, related_name="offer"
    )
    title = models.CharField(max_length=240)
    scope = models.TextField()
    price_eur = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status, default=Status.PROPOSED)
    accepted_at = models.DateTimeField(null=True, blank=True)
    is_synthetic = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.title


class SyntheticPayment(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer = models.OneToOneField(Offer, on_delete=models.PROTECT, related_name="payment")
    amount_eur = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    provider = models.CharField(max_length=40, default="internal-simulation")
    external_reference = models.CharField(max_length=200, blank=True)
    is_synthetic = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Synthetic payment €{self.amount_eur} ({self.status})"


class Deliverable(TimestampedModel):
    class Status(models.TextChoices):
        READY = "ready", "Ready for review"
        REVISION_REQUESTED = "revision_requested", "Revision requested"
        ACCEPTED = "accepted", "Accepted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_request = models.OneToOneField(
        CustomerRequest, on_delete=models.PROTECT, related_name="deliverable"
    )
    title = models.CharField(max_length=240)
    content = models.TextField()
    status = models.CharField(max_length=30, choices=Status, default=Status.READY)
    revision_note = models.TextField(blank=True)
    is_synthetic = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.title


class WorkflowRun(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting approval"
        RETRYING = "retrying", "Retrying"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    engagement = models.ForeignKey(
        Engagement,
        on_delete=models.PROTECT,
        related_name="workflow_runs",
    )
    workflow_key = models.SlugField()
    workflow_version = models.CharField(max_length=50, default="0.1")
    status = models.CharField(max_length=30, choices=Status, default=Status.PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    estimated_cost_eur = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.workflow_key} ({self.status})"


class Approval(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_run = models.ForeignKey(
        WorkflowRun,
        on_delete=models.PROTECT,
        related_name="approvals",
    )
    action_type = models.SlugField()
    status = models.CharField(max_length=20, choices=Status, default=Status.PENDING)
    request_payload = models.JSONField(default=dict, blank=True)
    decision_note = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="autobiz_approval_decisions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.action_type} ({self.status})"

    def clean(self):
        super().clean()
        terminal_decisions = {self.Status.APPROVED, self.Status.REJECTED}
        if self.status in terminal_decisions and (not self.decided_by or not self.decided_at):
            raise ValidationError(
                "Approved or rejected requests require a decision owner and time."
            )
        if self.status == self.Status.PENDING and (self.decided_by or self.decided_at):
            raise ValidationError("Pending requests cannot contain a completed decision.")


class AuditEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Audit events are append-only and cannot be modified.")

    def delete(self):
        raise ValidationError("Audit events are append-only and cannot be deleted.")


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_run = models.ForeignKey(
        WorkflowRun,
        on_delete=models.PROTECT,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    event_type = models.SlugField()
    actor = models.CharField(max_length=200)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager.from_queryset(AuditEventQuerySet)()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event_type", "created_at"])]

    def __str__(self) -> str:
        return f"{self.event_type} by {self.actor}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Audit events are append-only and cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only and cannot be deleted.")
