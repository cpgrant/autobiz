from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import ActionProposal, Approval, AuditEvent, Company


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
