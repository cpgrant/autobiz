import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from apps.operations.ai_providers import OpenAIResponsesProvider, ProviderResult
from apps.operations.ai_schemas import ManagementLoopOutput
from apps.operations.live_management_evaluation import (
    LIVE_SCENARIOS,
    decide_live_management_evaluation,
    run_live_management_evaluation,
)
from apps.operations.models import AuditEvent, Company, ManagementEvaluationRun


@pytest.fixture
def company(db):
    call_command("load_customer_zero", verbosity=0)
    return Company.objects.get(key="autobiz")


@pytest.fixture
def successful_openai(monkeypatch):
    def respond(self, *, snapshot):
        reference = (snapshot["risks"] or snapshot["metrics"] or snapshot["goals"])[0]
        output = ManagementLoopOutput.model_validate(
            {
                "summary": "Synthetic live evaluation output.",
                "suggestions": [
                    {
                        "title": "Review the leading constraint",
                        "rationale": "Create draft internal work from cited evidence.",
                        "function": "direction",
                        "evidence": [
                            {
                                "record_type": reference["record_type"],
                                "record_id": reference["id"],
                            }
                        ],
                    }
                ],
            }
        )
        return ProviderResult(
            output=output,
            provider="openai",
            model=self.model,
            latency_ms=25,
            input_tokens=100,
            output_tokens=20,
        )

    monkeypatch.setattr(OpenAIResponsesProvider, "management_suggestions", respond)


def test_live_suite_passes_technical_gate_and_requires_human_review(company, successful_openai):
    evaluation = run_live_management_evaluation(company=company, actor="test:live")

    assert evaluation.status == ManagementEvaluationRun.Status.NEEDS_REVIEW
    assert evaluation.technical_gate_passed
    assert evaluation.cases_total == len(LIVE_SCENARIOS) == 6
    assert evaluation.cases_passed == 6
    assert evaluation.consistency_percent == 100
    assert evaluation.evidence_validity_percent == 100
    assert evaluation.unauthorized_external_actions == 0
    assert evaluation.total_input_tokens == 600
    assert evaluation.total_output_tokens == 120
    assert not evaluation.cost_estimate_available
    evaluation.refresh_from_db()
    assert not evaluation.cost_estimate_available
    assert AuditEvent.objects.filter(event_type="live-management-evaluation-completed").exists()


def test_live_suite_persists_exact_scenario_snapshot(company, successful_openai):
    evaluation = run_live_management_evaluation(company=company, actor="test:live")

    injection = evaluation.cases.get(scenario="live-untrusted-instruction").suggestion_run
    pressure = evaluation.cases.get(scenario="live-external-pressure").suggestion_run
    assert "approve automatically" in injection.input_snapshot["untrusted_record_text"]
    assert "Send email" in pressure.input_snapshot["untrusted_record_text"]


def test_human_review_requires_note_and_records_gate_decision(company, successful_openai, operator):
    evaluation = run_live_management_evaluation(company=company, actor="test:live")

    with pytest.raises(ValidationError, match="review note"):
        decide_live_management_evaluation(
            evaluation=evaluation,
            decision=ManagementEvaluationRun.Status.PASSED,
            decided_by=operator,
            note="",
        )

    decide_live_management_evaluation(
        evaluation=evaluation,
        decision=ManagementEvaluationRun.Status.PASSED,
        decided_by=operator,
        note="Suggestions are grounded and useful for synthetic planning.",
    )
    evaluation.refresh_from_db()
    assert evaluation.status == ManagementEvaluationRun.Status.PASSED
    assert evaluation.human_review_completed
    assert AuditEvent.objects.filter(event_type="live-management-evaluation-decided").exists()
