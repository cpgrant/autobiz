from decimal import Decimal

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.operations.models import ActionProposal, Approval, AuditEvent, Company, Metric, WorkItem
from apps.operations.services import can_execute_action, refresh_company_state


@pytest.fixture
def customer_zero(db):
    call_command("load_customer_zero", verbosity=0)
    return Company.objects.get(key="autobiz")


def test_state_refresh_calculates_metrics_and_priorities(customer_zero):
    result = refresh_company_state(company=customer_zero, actor="test:operator")

    assert result.metrics_updated == 9
    assert Metric.objects.get(company=customer_zero, key="pipeline-value").value == Decimal(
        "3950.00"
    )
    assert Metric.objects.get(company=customer_zero, key="synthetic-revenue").value == Decimal(
        "1200.00"
    )
    assert Metric.objects.get(company=customer_zero, key="synthetic-costs").value == Decimal(
        "185.00"
    )
    assert WorkItem.objects.get(company=customer_zero, key="pilot-checklist").priority == 1
    assert WorkItem.objects.get(company=customer_zero, key="draft-follow-up").priority == 1
    assert WorkItem.objects.get(company=customer_zero, key="risk-review").priority == 2
    assert WorkItem.objects.get(company=customer_zero, key="qualify-atlas").priority == 3
    assert AuditEvent.objects.filter(event_type="company-state-refreshed").exists()


def test_operator_console_requires_staff(client, customer_zero, operator):
    response = client.get(reverse("operator-dashboard"))
    assert response.status_code == 302
    assert "/admin/login/" in response.url

    operator.is_staff = True
    operator.save(update_fields=["is_staff"])
    client.force_login(operator)
    response = client.get(reverse("operator-dashboard"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Operator console" in content
    assert "Pending approvals" in content
    assert "send-communication" in content
    assert "External actions remain disabled" in content


def test_operator_approval_updates_proposal_but_does_not_enable_execution(
    client, customer_zero, operator
):
    operator.is_staff = True
    operator.save(update_fields=["is_staff"])
    client.force_login(operator)
    approval = Approval.objects.get(status=Approval.Status.PENDING)

    response = client.post(
        reverse(
            "operator-decide-approval",
            kwargs={"approval_id": approval.pk, "decision": Approval.Status.APPROVED},
        ),
        {"note": "Synthetic review only."},
    )

    assert response.status_code == 302
    approval.refresh_from_db()
    proposal = ActionProposal.objects.get(approval=approval)
    assert approval.status == Approval.Status.APPROVED
    assert proposal.status == ActionProposal.Status.AUTHORIZED
    assert not can_execute_action(company=customer_zero, proposal=proposal)
    assert AuditEvent.objects.filter(event_type="approval-decided").exists()


def test_operator_can_refresh_state(client, customer_zero, operator):
    operator.is_staff = True
    operator.save(update_fields=["is_staff"])
    client.force_login(operator)

    response = client.post(reverse("operator-refresh"))

    assert response.status_code == 302
    assert Metric.objects.filter(company=customer_zero).count() == 9
