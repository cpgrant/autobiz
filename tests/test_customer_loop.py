import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from apps.operations.ai_providers import FakeAIProvider
from apps.operations.customer_loop import decide_customer_draft, run_customer_loop
from apps.operations.models import (
    Company,
    CustomerDraft,
    CustomerDraftRun,
    OperationsEvaluationRun,
)
from apps.operations.services import submit_synthetic_request


@pytest.fixture
def company(db):
    call_command("load_customer_zero", verbosity=0)
    company = Company.objects.get(key="autobiz")
    OperationsEvaluationRun.objects.create(
        company=company,
        status=OperationsEvaluationRun.Status.PASSED,
        provider="openai",
        technical_gate_passed=True,
        human_review_completed=True,
        human_review_note="Approved Operations fixture.",
    )
    submit_synthetic_request(
        customer_name="Synthetic Customer Loop",
        email="customer-loop@example.invalid",
        request_text="Please outline the next internal step.",
        desired_outcome="A controlled synthetic acknowledgement.",
    )
    return company


def test_customer_loop_requires_operations_human_gate(company):
    company.operations_evaluation_runs.all().delete()
    with pytest.raises(ValidationError, match="Operations Loop gate"):
        run_customer_loop(company=company, actor="test", provider=FakeAIProvider())


def test_customer_loop_creates_grounded_unsent_draft(company):
    result = run_customer_loop(company=company, actor="test", provider=FakeAIProvider())
    draft = result.run.drafts.get()

    assert result.run.status == CustomerDraftRun.Status.COMPLETED
    assert draft.validation_errors == []
    assert draft.status == CustomerDraft.Status.PENDING
    assert draft.sent_at is None
    assert draft.evidence[0]["record_type"] == "customer_request"


def test_approval_marks_draft_only_and_does_not_send(company, operator):
    draft = run_customer_loop(
        company=company, actor="test", provider=FakeAIProvider()
    ).run.drafts.get()

    decide_customer_draft(
        draft=draft,
        decision=CustomerDraft.Status.APPROVED,
        decided_by=operator,
        note="Grounded and appropriately bounded.",
    )

    draft.refresh_from_db()
    assert draft.status == CustomerDraft.Status.APPROVED
    assert draft.sent_at is None


def test_operator_can_generate_and_approve_customer_draft(client, company, operator):
    operator.is_staff = True
    operator.save(update_fields=["is_staff"])
    client.force_login(operator)

    assert client.post(reverse("operator-run-customer-loop")).status_code == 302
    draft = CustomerDraft.objects.get()
    response = client.post(
        reverse(
            "operator-decide-customer-draft",
            kwargs={"draft_id": draft.pk, "decision": CustomerDraft.Status.APPROVED},
        ),
        {"note": "Safe draft."},
    )
    assert response.status_code == 302
    draft.refresh_from_db()
    assert draft.status == CustomerDraft.Status.APPROVED
    assert draft.sent_at is None
