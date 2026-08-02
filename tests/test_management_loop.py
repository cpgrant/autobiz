import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from apps.operations.ai_providers import FakeAIProvider, ProviderResult
from apps.operations.ai_schemas import ManagementLoopOutput
from apps.operations.management_loop import decide_suggestion, run_management_loop
from apps.operations.models import AuditEvent, Company, Suggestion, SuggestionRun, WorkItem


@pytest.fixture
def company(db):
    call_command("load_customer_zero", verbosity=0)
    return Company.objects.get(key="autobiz")


def test_fake_provider_creates_evidence_validated_pending_suggestion(company):
    result = run_management_loop(company=company, actor="test:operator", provider=FakeAIProvider())

    assert result.run.status == SuggestionRun.Status.COMPLETED
    assert result.run.provider == "fake"
    suggestion = result.run.suggestions.get()
    assert suggestion.status == Suggestion.Status.PENDING
    assert suggestion.validation_errors == []
    assert suggestion.evidence
    assert AuditEvent.objects.filter(event_type="management-suggestions-generated").exists()


def test_unknown_evidence_is_recorded_and_blocks_acceptance(company, operator):
    class UnknownEvidenceProvider:
        def management_suggestions(self, *, snapshot):
            output = ManagementLoopOutput.model_validate(
                {
                    "summary": "Test",
                    "suggestions": [
                        {
                            "title": "Unsupported suggestion",
                            "rationale": "No matching evidence.",
                            "function": "direction",
                            "evidence": [{"record_type": "risk", "record_id": "missing"}],
                        }
                    ],
                }
            )
            return ProviderResult(output=output, provider="test", model="invalid-evidence")

    run_management_loop(company=company, actor="test:operator", provider=UnknownEvidenceProvider())
    suggestion = Suggestion.objects.get(title="Unsupported suggestion")

    assert suggestion.validation_errors
    with pytest.raises(ValidationError, match="validation errors"):
        decide_suggestion(
            suggestion=suggestion,
            decision=Suggestion.Status.ACCEPTED,
            decided_by=operator,
        )
    assert not WorkItem.objects.filter(title="Unsupported suggestion").exists()


def test_acceptance_creates_only_proposed_draft_work(company, operator):
    result = run_management_loop(company=company, actor="test:operator", provider=FakeAIProvider())
    suggestion = result.run.suggestions.get()

    decide_suggestion(
        suggestion=suggestion,
        decision=Suggestion.Status.ACCEPTED,
        decided_by=operator,
        note="Worth testing.",
    )

    suggestion.refresh_from_db()
    assert suggestion.work_item.status == WorkItem.Status.PROPOSED
    assert suggestion.work_item.is_synthetic
    assert not suggestion.work_item.requires_approval
    assert not company.external_execution_enabled


def test_provider_failure_is_durable_and_safe(company):
    class FailingProvider:
        def management_suggestions(self, *, snapshot):
            raise TimeoutError("synthetic timeout")

    result = run_management_loop(company=company, actor="test:operator", provider=FailingProvider())

    assert result.run.status == SuggestionRun.Status.FAILED
    assert result.run.error_code == "TimeoutError"
    assert result.suggestions_created == 0
    assert AuditEvent.objects.filter(event_type="management-suggestion-run-failed").exists()


def test_operator_can_generate_and_decide_suggestion(client, company, operator):
    operator.is_staff = True
    operator.save(update_fields=["is_staff"])
    client.force_login(operator)

    response = client.post(reverse("operator-run-management-loop"))
    assert response.status_code == 302
    suggestion = Suggestion.objects.get()

    response = client.post(
        reverse(
            "operator-decide-suggestion",
            kwargs={"suggestion_id": suggestion.pk, "decision": Suggestion.Status.DEFERRED},
        )
    )
    assert response.status_code == 302
    suggestion.refresh_from_db()
    assert suggestion.status == Suggestion.Status.DEFERRED

    page = client.get(reverse("operator-dashboard")).content.decode()
    assert "Management Loop suggestions" in page
    assert "Deferred" in page
