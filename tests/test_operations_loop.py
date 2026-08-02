import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from apps.operations.ai_providers import FakeAIProvider
from apps.operations.models import (
    AuditEvent,
    Company,
    ManagementEvaluationRun,
    Suggestion,
    SuggestionRun,
    WorkItem,
)
from apps.operations.operations_loop import run_operations_loop


@pytest.fixture
def company(db):
    call_command("load_customer_zero", verbosity=0)
    company = Company.objects.get(key="autobiz")
    ManagementEvaluationRun.objects.create(
        company=company,
        status=ManagementEvaluationRun.Status.PASSED,
        provider="openai",
        technical_gate_passed=True,
        human_review_completed=True,
        human_review_note="Human-approved Management gate fixture.",
    )
    return company


def test_operations_loop_requires_passed_management_human_gate(company):
    company.management_evaluation_runs.all().delete()

    with pytest.raises(ValidationError, match="Management Loop gate"):
        run_operations_loop(company=company, actor="test", provider=FakeAIProvider())


def test_operations_loop_creates_grounded_pending_draft(company):
    result = run_operations_loop(company=company, actor="test", provider=FakeAIProvider())

    assert result.run.loop == SuggestionRun.Loop.OPERATIONS
    assert result.run.operating_cycle is not None
    suggestion = result.run.suggestions.get()
    assert suggestion.status == Suggestion.Status.PENDING
    assert suggestion.validation_errors == []
    assert suggestion.evidence[0]["record_type"] == "operating_cycle"
    assert not WorkItem.objects.filter(title=suggestion.title).exists()
    assert AuditEvent.objects.filter(event_type="operations-suggestions-generated").exists()


def test_operator_can_generate_operations_suggestion(client, company, operator):
    operator.is_staff = True
    operator.save(update_fields=["is_staff"])
    client.force_login(operator)

    response = client.post(reverse("operator-run-operations-loop"))

    assert response.status_code == 302
    assert Suggestion.objects.filter(run__loop=SuggestionRun.Loop.OPERATIONS).exists()
    page = client.get(reverse("operator-dashboard")).content.decode()
    assert "Operations Loop" in page
    assert "Pass Operations gate" not in page
