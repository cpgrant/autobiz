from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
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
    Offer,
    Opportunity,
    Product,
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
        defaults={
            "title": "Controlled operating plan",
            "content": _operating_plan_content(locked),
            "is_synthetic": True,
        },
    )
    return deliverable


@transactional
def review_deliverable(
    *, customer_request: CustomerRequest, decision: str, revision_note: str = ""
) -> Deliverable:
    deliverable = Deliverable.objects.select_for_update().get(customer_request=customer_request)
    locked = CustomerRequest.objects.select_for_update().get(pk=customer_request.pk)
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
