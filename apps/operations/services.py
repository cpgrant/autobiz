from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Approval, AuditEvent


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
