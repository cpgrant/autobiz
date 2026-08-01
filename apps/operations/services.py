from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

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
    Metric,
    Offer,
    OperatingCycle,
    Opportunity,
    Product,
    Risk,
    SyntheticPayment,
    WorkItem,
)


def transactional[ServiceFunction: Callable[..., Any]](func: ServiceFunction) -> ServiceFunction:
    """Preserve service signatures while applying Django's atomic decorator."""
    return cast(ServiceFunction, transaction.atomic(func))


@dataclass(frozen=True)
class AuthorityRule:
    level: int
    requires_approval: bool
    external: bool = False
    executor_available: bool = True


AUTHORITY_RULES = {
    "read-local-records": AuthorityRule(ActionProposal.AuthorityLevel.OBSERVE, False),
    "calculate-metrics": AuthorityRule(ActionProposal.AuthorityLevel.OBSERVE, False),
    "prioritize-work": AuthorityRule(ActionProposal.AuthorityLevel.DRAFT, False),
    "draft-plan": AuthorityRule(ActionProposal.AuthorityLevel.DRAFT, False),
    "draft-report": AuthorityRule(ActionProposal.AuthorityLevel.DRAFT, False),
    "create-simulated-task": AuthorityRule(ActionProposal.AuthorityLevel.BOUNDED_EXECUTE, False),
    "simulate-reversible-outcome": AuthorityRule(
        ActionProposal.AuthorityLevel.BOUNDED_EXECUTE, False
    ),
    "send-communication": AuthorityRule(
        ActionProposal.AuthorityLevel.HUMAN_APPROVAL, True, True, False
    ),
    "spend-money": AuthorityRule(ActionProposal.AuthorityLevel.HUMAN_APPROVAL, True, True, False),
    "change-price": AuthorityRule(ActionProposal.AuthorityLevel.HUMAN_APPROVAL, True, True, False),
    "make-contractual-commitment": AuthorityRule(
        ActionProposal.AuthorityLevel.PROHIBITED, True, True, False
    ),
    "delete-record": AuthorityRule(
        ActionProposal.AuthorityLevel.HUMAN_APPROVAL, True, False, False
    ),
    "access-external-system": AuthorityRule(
        ActionProposal.AuthorityLevel.PROHIBITED, True, True, False
    ),
    "publish-content": AuthorityRule(
        ActionProposal.AuthorityLevel.HUMAN_APPROVAL, True, True, False
    ),
}


def authority_rule_for(action_type: str) -> AuthorityRule:
    """Return the deterministic authority rule; unknown actions fail closed."""
    return AUTHORITY_RULES.get(
        action_type,
        AuthorityRule(ActionProposal.AuthorityLevel.PROHIBITED, True, False, False),
    )


def can_execute_action(*, company: Company, proposal: ActionProposal) -> bool:
    """Evaluate execution independently from approval state and fail closed."""
    if proposal.authority_level == ActionProposal.AuthorityLevel.PROHIBITED:
        return False
    if not proposal.executor_available:
        return False
    if proposal.is_external and not company.external_execution_enabled:
        return False
    if proposal.requires_approval:
        return bool(proposal.approval and proposal.approval.status == Approval.Status.APPROVED)
    return proposal.authority_level <= ActionProposal.AuthorityLevel.BOUNDED_EXECUTE


@dataclass(frozen=True)
class CompanyStateRefresh:
    metrics_updated: int
    work_items_prioritized: int
    audit_event: AuditEvent


def deterministic_priority(work_item: WorkItem) -> int:
    """Assign a documented 1–5 priority using authoritative workflow state."""
    if work_item.status == WorkItem.Status.DONE:
        return 5
    if work_item.status == WorkItem.Status.IN_PROGRESS:
        return 1
    if work_item.status == WorkItem.Status.BLOCKED and work_item.requires_approval:
        return 1
    if work_item.key.startswith("revision-") and work_item.status == WorkItem.Status.READY:
        return 1
    if work_item.status == WorkItem.Status.READY:
        return 2
    if work_item.status == WorkItem.Status.BLOCKED:
        return 2
    return 3


def _metric_values(company: Company) -> list[tuple[str, str, Decimal, Decimal | None, str]]:
    open_opportunities = company.opportunities.exclude(
        stage__in=[Opportunity.Stage.WON, Opportunity.Stage.LOST]
    )
    weighted_pipeline = sum(
        (
            opportunity.estimated_value_eur
            * Decimal(opportunity.probability_percent)
            / Decimal(100)
            for opportunity in open_opportunities
        ),
        Decimal(0),
    )
    revenue = company.financial_entries.filter(
        entry_type=FinancialEntry.EntryType.REVENUE
    ).aggregate(total=Sum("amount_eur"))["total"] or Decimal(0)
    costs = company.financial_entries.filter(entry_type=FinancialEntry.EntryType.COST).aggregate(
        total=Sum("amount_eur")
    )["total"] or Decimal(0)
    total_work = company.work_items.count()
    completed_work = company.work_items.filter(status=WorkItem.Status.DONE).count()
    completion_rate = (
        Decimal(completed_work) * Decimal(100) / Decimal(total_work) if total_work else Decimal(0)
    )
    terminal_approvals = Approval.objects.filter(
        workflow_run__engagement__customer__company=company,
        status__in=[Approval.Status.APPROVED, Approval.Status.REJECTED],
    )
    terminal_count = terminal_approvals.count()
    approval_rate = (
        Decimal(terminal_approvals.filter(status=Approval.Status.APPROVED).count())
        * Decimal(100)
        / Decimal(terminal_count)
        if terminal_count
        else Decimal(0)
    )
    return [
        (
            "cycle-completion",
            "Completed operating cycles",
            Decimal(
                company.operating_cycles.filter(status=OperatingCycle.Status.COMPLETED).count()
            ),
            Decimal(10),
            "cycles",
        ),
        ("approval-rate", "Approval rate", approval_rate, Decimal(80), "percent"),
        (
            "unauthorized-actions",
            "Unauthorized external actions",
            Decimal(
                AuditEvent.objects.filter(
                    event_type="unauthorized-external-action",
                    payload__company_id=str(company.pk),
                ).count()
            ),
            Decimal(0),
            "actions",
        ),
        ("pipeline-value", "Weighted pipeline value", weighted_pipeline, Decimal(5000), "EUR"),
        (
            "open-opportunities",
            "Open opportunities",
            Decimal(open_opportunities.count()),
            None,
            "opportunities",
        ),
        ("synthetic-revenue", "Synthetic revenue", revenue, None, "EUR"),
        ("synthetic-costs", "Synthetic costs", costs, None, "EUR"),
        ("work-completion", "Work completion", completion_rate, Decimal(90), "percent"),
        (
            "open-risks",
            "Open risks",
            Decimal(company.risks.filter(status=Risk.Status.OPEN).count()),
            Decimal(0),
            "risks",
        ),
    ]


@transactional
def refresh_company_state(*, company: Company, actor: str) -> CompanyStateRefresh:
    """Recalculate metrics and work priorities without running an operating cycle."""
    metrics_updated = 0
    for key, name, value, target, unit in _metric_values(company):
        Metric.objects.update_or_create(
            company=company,
            key=key,
            defaults={
                "name": name,
                "value": value.quantize(Decimal("0.01")),
                "target_value": target,
                "unit": unit,
                "is_synthetic": True,
            },
        )
        metrics_updated += 1

    work_items_prioritized = 0
    for work_item in company.work_items.all():
        priority = deterministic_priority(work_item)
        if work_item.priority != priority:
            work_item.priority = priority
            work_item.save(update_fields=["priority", "updated_at"])
        work_items_prioritized += 1

    audit_event = AuditEvent.objects.create(
        event_type="company-state-refreshed",
        actor=actor,
        payload={
            "company_id": str(company.pk),
            "metrics_updated": metrics_updated,
            "work_items_prioritized": work_items_prioritized,
            "synthetic": True,
        },
    )
    return CompanyStateRefresh(metrics_updated, work_items_prioritized, audit_event)


@dataclass(frozen=True)
class SubmittedRequest:
    customer_request: CustomerRequest
    offer: Offer


@transactional
def submit_synthetic_request(
    *, customer_name: str, email: str, request_text: str, desired_outcome: str
) -> SubmittedRequest:
    """Create a local synthetic request and deterministic Establish offer."""
    company = Company.objects.get(key="autobiz")
    product = Product.objects.get(company=company, key="establish", is_synthetic=True)
    customer = Customer.objects.create(
        company=company,
        name=customer_name,
        primary_email=email,
        status=Customer.Status.PROSPECT,
        notes="SYNTHETIC — submitted through the local Customer Zero portal.",
        is_synthetic=True,
    )
    customer_request = CustomerRequest.objects.create(
        company=company,
        customer=customer,
        product=product,
        request_text=request_text,
        desired_outcome=desired_outcome,
        status=CustomerRequest.Status.OFFERED,
        is_synthetic=True,
    )
    key_suffix = customer_request.pk.hex[:12]
    Opportunity.objects.create(
        company=company,
        key=f"portal-{key_suffix}",
        customer=customer,
        product=product,
        stage=Opportunity.Stage.PROPOSED,
        estimated_value_eur=1200,
        probability_percent=60,
        is_synthetic=True,
    )
    offer = Offer.objects.create(
        customer_request=customer_request,
        title="Establish · Controlled operating plan",
        scope=(
            "A local operating-plan package covering objectives, five company functions, "
            "priorities, operating rhythm, KPIs, authority boundaries, risks, and a 30-day plan."
        ),
        price_eur=1200,
        is_synthetic=True,
    )
    AuditEvent.objects.create(
        event_type="synthetic-request-submitted",
        actor="customer:synthetic-portal",
        payload={
            "customer_request_id": str(customer_request.pk),
            "customer_id": str(customer.pk),
            "offer_id": str(offer.pk),
            "synthetic": True,
        },
    )
    return SubmittedRequest(customer_request=customer_request, offer=offer)


@transactional
def accept_synthetic_offer(*, customer_request: CustomerRequest) -> Offer:
    """Accept the fixed synthetic offer without creating a real commitment."""
    locked = CustomerRequest.objects.select_for_update().get(pk=customer_request.pk)
    offer = Offer.objects.select_for_update().get(customer_request=locked)
    if offer.status == Offer.Status.PROPOSED:
        offer.status = Offer.Status.ACCEPTED
        offer.accepted_at = timezone.now()
        offer.save(update_fields=["status", "accepted_at", "updated_at"])
        locked.status = CustomerRequest.Status.ACCEPTED
        locked.save(update_fields=["status", "updated_at"])
        AuditEvent.objects.create(
            event_type="synthetic-offer-accepted",
            actor="customer:synthetic-portal",
            payload={"customer_request_id": str(locked.pk), "synthetic": True},
        )
    return offer


def _operating_plan_content(customer_request: CustomerRequest) -> str:
    return f"""SYNTHETIC CUSTOMER ZERO DELIVERABLE

Customer: {customer_request.customer.name}
Service: Establish
Request: {customer_request.request_text}
Desired outcome: {customer_request.desired_outcome}

1. Objective
Establish a visible and controlled operating system around the stated outcome.

2. Five-function operating model
Direction sets goals and priorities. Growth manages evidence and opportunities.
Delivery owns work and quality. Finance tracks synthetic economics. Operations
controls approvals, risks, audit history, and reporting.

3. Initial priorities
- Confirm one measurable 30-day objective.
- Map current work and identify the leading constraint.
- Establish a weekly operating review and decision log.
- Track exceptions and require approval for consequential actions.

4. Operating rhythm
Daily: inspect state, prioritize work, execute bounded actions, and record results.
Weekly: review metrics, exceptions, finances, and strategic options.

5. Initial KPIs
- Priority work completed on time.
- Open exceptions and average resolution time.
- Approval rate and unauthorized actions (target: zero).
- Synthetic revenue, cost, and contribution.

6. Authority boundary
Analysis, drafts, and reversible internal simulations are permitted. External
communications, spending, price changes, publication, and commitments require
human control. External execution remains disabled.

7. Thirty-day plan
Week 1: baseline goals, work, metrics, and controls.
Week 2: run deterministic daily cycles and measure exceptions.
Week 3: improve the leading bottleneck and verify recovery behavior.
Week 4: review evidence and decide what to continue, change, or stop.
"""


@transactional
def simulate_payment_and_delivery(*, customer_request: CustomerRequest) -> Deliverable:
    """Record test money and create local work and a deterministic deliverable once."""
    locked = CustomerRequest.objects.select_for_update().get(pk=customer_request.pk)
    offer = Offer.objects.select_for_update().get(customer_request=locked)
    if offer.status != Offer.Status.ACCEPTED:
        raise ValidationError("The synthetic offer must be accepted before payment.")

    payment, created = SyntheticPayment.objects.get_or_create(
        offer=offer,
        defaults={
            "amount_eur": offer.price_eur,
            "status": SyntheticPayment.Status.PAID,
            "paid_at": timezone.now(),
            "external_reference": f"sim-{locked.pk.hex[:12]}",
            "is_synthetic": True,
        },
    )
    if created:
        locked.customer.status = Customer.Status.PILOT
        locked.customer.save(update_fields=["status", "updated_at"])
        engagement = Engagement.objects.create(
            customer=locked.customer,
            product=locked.product,
            status=Engagement.Status.PILOT,
            starts_on=timezone.localdate(),
            is_synthetic=True,
        )
        locked.engagement = engagement
        FinancialEntry.objects.create(
            company=locked.company,
            key=f"portal-payment-{locked.pk.hex[:12]}",
            entry_type=FinancialEntry.EntryType.REVENUE,
            description=f"Synthetic Establish payment from {locked.customer.name}",
            amount_eur=payment.amount_eur,
            occurred_on=timezone.localdate(),
            is_synthetic=True,
        )
        for position, title in enumerate(
            [
                "Confirm objective and desired outcome",
                "Draft the controlled operating plan",
                "Review authority boundaries and risks",
                "Deliver operating plan for customer review",
            ],
            start=1,
        ):
            WorkItem.objects.create(
                company=locked.company,
                engagement=engagement,
                key=f"portal-{locked.pk.hex[:8]}-{position}",
                title=title,
                function=(
                    WorkItem.Function.DIRECTION if position == 1 else WorkItem.Function.DELIVERY
                ),
                status=WorkItem.Status.DONE,
                priority=position,
                is_synthetic=True,
            )
        Opportunity.objects.filter(
            company=locked.company, key=f"portal-{locked.pk.hex[:12]}"
        ).update(stage=Opportunity.Stage.WON, probability_percent=100)
        locked.status = CustomerRequest.Status.DELIVERED
        locked.save(update_fields=["engagement", "status", "updated_at"])
        AuditEvent.objects.create(
            event_type="synthetic-payment-recorded",
            actor="system:internal-payment-simulator",
            payload={
                "customer_request_id": str(locked.pk),
                "payment_id": str(payment.pk),
                "amount_eur": str(payment.amount_eur),
                "synthetic": True,
            },
        )
    deliverable, _ = Deliverable.objects.get_or_create(
        customer_request=locked,
        version=1,
        defaults={
            "title": "Controlled operating plan",
            "content": _operating_plan_content(locked),
            "is_current": True,
            "is_synthetic": True,
        },
    )
    return deliverable


@transactional
def review_deliverable(
    *, customer_request: CustomerRequest, decision: str, revision_note: str = ""
) -> Deliverable:
    deliverable = Deliverable.objects.select_for_update().get(
        customer_request=customer_request, is_current=True
    )
    locked = CustomerRequest.objects.select_for_update().get(pk=customer_request.pk)
    if deliverable.status != Deliverable.Status.READY:
        raise ValidationError("Only a deliverable ready for review can be decided.")
    if decision == "accept":
        deliverable.status = Deliverable.Status.ACCEPTED
        deliverable.revision_note = ""
        locked.status = CustomerRequest.Status.COMPLETED
        event_type = "synthetic-deliverable-accepted"
    elif decision == "revise" and revision_note.strip():
        deliverable.status = Deliverable.Status.REVISION_REQUESTED
        deliverable.revision_note = revision_note.strip()
        locked.status = CustomerRequest.Status.REVISION_REQUESTED
        event_type = "synthetic-deliverable-revision-requested"
        WorkItem.objects.get_or_create(
            company=locked.company,
            key=f"revision-{locked.pk.hex[:8]}-v{deliverable.version + 1}",
            defaults={
                "engagement": locked.engagement,
                "title": f"Produce deliverable version {deliverable.version + 1}",
                "function": WorkItem.Function.DELIVERY,
                "status": WorkItem.Status.READY,
                "priority": 1,
                "is_synthetic": True,
            },
        )
    else:
        raise ValidationError("Choose accept or provide a revision request.")
    deliverable.save(update_fields=["status", "revision_note", "updated_at"])
    locked.save(update_fields=["status", "updated_at"])
    AuditEvent.objects.create(
        event_type=event_type,
        actor="customer:synthetic-portal",
        payload={"customer_request_id": str(locked.pk), "synthetic": True},
    )
    return deliverable


def _revised_operating_plan_content(deliverable: Deliverable) -> str:
    return f"""{deliverable.content}

8. Revision changes in version {int(deliverable.version) + 1}
Customer revision request: {deliverable.revision_note}

Named owners
- Founder/operator: confirm goals, approve consequential decisions, and own the weekly review.
- Direction: maintain priorities and decision records.
- Delivery: complete weekly actions and quality checks.
- Finance: prepare the cash-flow review and reconcile synthetic entries.
- Operations: track exceptions, approvals, and audit evidence.

Measurable success targets
- Complete at least 90% of committed weekly priority work.
- Resolve high-severity exceptions within one business day.
- Keep unauthorized external actions at zero.
- Review cash position, expected receipts, costs, and 30-day runway every week.

Weekly cash-flow review
Review opening cash, synthetic revenue, committed costs, expected closing cash,
exceptions, and any spending decision requiring human approval.
"""


@transactional
def produce_revised_deliverable(*, customer_request: CustomerRequest) -> Deliverable:
    """Simulate bounded internal revision work while retaining prior versions."""
    locked = CustomerRequest.objects.select_for_update().get(pk=customer_request.pk)
    current = Deliverable.objects.select_for_update().get(customer_request=locked, is_current=True)
    if current.status != Deliverable.Status.REVISION_REQUESTED:
        raise ValidationError("The current deliverable does not have a revision request.")

    new_version = int(current.version) + 1
    revision_work, _ = WorkItem.objects.get_or_create(
        company=locked.company,
        key=f"revision-{locked.pk.hex[:8]}-v{new_version}",
        defaults={
            "engagement": locked.engagement,
            "title": f"Produce deliverable version {new_version}",
            "function": WorkItem.Function.DELIVERY,
            "status": WorkItem.Status.READY,
            "priority": 1,
            "is_synthetic": True,
        },
    )
    current.is_current = False
    current.save(update_fields=["is_current", "updated_at"])
    revised = Deliverable.objects.create(
        customer_request=locked,
        version=new_version,
        is_current=True,
        title=f"Controlled operating plan · Version {new_version}",
        content=_revised_operating_plan_content(current),
        status=Deliverable.Status.READY,
        is_synthetic=True,
    )
    revision_work.status = WorkItem.Status.DONE
    revision_work.save(update_fields=["status", "updated_at"])
    locked.status = CustomerRequest.Status.DELIVERED
    locked.save(update_fields=["status", "updated_at"])
    AuditEvent.objects.create(
        event_type="synthetic-deliverable-revised",
        actor="system:customer-zero-revision-simulator",
        payload={
            "customer_request_id": str(locked.pk),
            "previous_deliverable_id": str(current.pk),
            "deliverable_id": str(revised.pk),
            "version": new_version,
            "synthetic": True,
        },
    )
    return revised


@dataclass(frozen=True)
class ApprovalDecision:
    approval: Approval
    audit_event: AuditEvent


def decide_approval(
    *,
    approval: Approval,
    decision: str,
    decided_by: AbstractBaseUser,
    note: str = "",
) -> ApprovalDecision:
    """Make a terminal approval decision and append its audit event."""
    with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
        locked = Approval.objects.select_for_update().get(pk=approval.pk)
        allowed = {Approval.Status.APPROVED, Approval.Status.REJECTED}

        if locked.status != Approval.Status.PENDING:
            raise ValidationError("Only pending approvals can be decided.")
        if decision not in allowed:
            raise ValidationError("Decision must be approved or rejected.")

        locked.status = decision
        locked.decided_by = decided_by
        locked.decided_at = timezone.now()
        locked.decision_note = note
        locked.full_clean()
        locked.save(
            update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"]
        )

        if hasattr(locked, "action_proposal"):
            proposal = locked.action_proposal
            proposal.status = (
                ActionProposal.Status.AUTHORIZED
                if decision == Approval.Status.APPROVED
                else ActionProposal.Status.REJECTED
            )
            proposal.save(update_fields=["status", "updated_at"])

        audit_event = AuditEvent.objects.create(
            workflow_run=locked.workflow_run,
            event_type="approval-decided",
            actor=f"user:{decided_by.pk}",
            payload={
                "approval_id": str(locked.pk),
                "action_type": locked.action_type,
                "decision": decision,
            },
        )
        return ApprovalDecision(approval=locked, audit_event=audit_event)
