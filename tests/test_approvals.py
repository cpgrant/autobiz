from typing import cast

import pytest
from django.core.exceptions import ValidationError

from apps.operations.models import Approval, AuditEvent
from apps.operations.services import decide_approval


@pytest.mark.django_db
def test_decide_approval_records_owner_time_and_append_only_audit(workflow_run, operator):
    approval = Approval.objects.create(
        workflow_run=workflow_run,
        action_type="generic-controlled-action",
    )

    result = decide_approval(
        approval=approval,
        decision=Approval.Status.APPROVED,
        decided_by=operator,
        note="Reviewed in test.",
    )

    assert result.approval.status == Approval.Status.APPROVED
    assert result.approval.decided_by == operator
    assert result.approval.decided_at is not None
    payload = cast(dict[str, object], result.audit_event.payload)
    assert payload["approval_id"] == str(approval.pk)
    assert payload["decision"] == Approval.Status.APPROVED


@pytest.mark.django_db
def test_approval_cannot_be_decided_twice(workflow_run, operator):
    approval = Approval.objects.create(workflow_run=workflow_run, action_type="generic-action")
    decide_approval(
        approval=approval,
        decision=Approval.Status.REJECTED,
        decided_by=operator,
    )

    with pytest.raises(ValidationError, match="Only pending"):
        decide_approval(
            approval=approval,
            decision=Approval.Status.APPROVED,
            decided_by=operator,
        )


@pytest.mark.django_db
def test_invalid_approval_decision_is_rejected(workflow_run, operator):
    approval = Approval.objects.create(workflow_run=workflow_run, action_type="generic-action")

    with pytest.raises(ValidationError, match="approved or rejected"):
        decide_approval(approval=approval, decision="maybe", decided_by=operator)


@pytest.mark.django_db
def test_audit_event_cannot_be_changed_or_deleted(workflow_run):
    event = AuditEvent.objects.create(
        workflow_run=workflow_run,
        event_type="control-tested",
        actor="test-suite",
    )
    event.actor = "changed"

    with pytest.raises(ValidationError, match="append-only"):
        event.save()
    with pytest.raises(ValidationError, match="append-only"):
        event.delete()
    with pytest.raises(ValidationError, match="append-only"):
        AuditEvent.objects.filter(pk=event.pk).update(actor="changed")
    with pytest.raises(ValidationError, match="append-only"):
        AuditEvent.objects.filter(pk=event.pk).delete()
