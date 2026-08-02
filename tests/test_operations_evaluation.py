import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from apps.operations.ai_providers import OpenAIResponsesProvider, OperationsProviderResult
from apps.operations.ai_schemas import OperationsLoopOutput
from apps.operations.models import (
    AuditEvent,
    Company,
    ManagementEvaluationRun,
    OperationsEvaluationRun,
)
from apps.operations.operations_evaluation import (
    LIVE_SCENARIOS,
    OFFLINE_SCENARIOS,
    decide_operations_evaluation,
    run_operations_evaluation,
)


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


@pytest.fixture
def successful_openai(monkeypatch):
    def respond(self, *, snapshot):
        cycle = snapshot["operating_cycles"][0]
        return OperationsProviderResult(
            output=OperationsLoopOutput.model_validate(
                {
                    "summary": "Synthetic Operations evaluation output.",
                    "exceptions": [],
                    "suggestions": [
                        {
                            "title": "Review the completed operating cycle",
                            "rationale": "Draft one internal improvement from cycle evidence.",
                            "function": "operations",
                            "evidence": [
                                {
                                    "record_type": "operating_cycle",
                                    "record_id": cycle["id"],
                                }
                            ],
                        }
                    ],
                }
            ),
            provider="openai",
            model=self.model,
            latency_ms=20,
            input_tokens=90,
            output_tokens=18,
        )

    monkeypatch.setattr(OpenAIResponsesProvider, "operations_suggestions", respond)


def test_offline_operations_suite_passes(company):
    evaluation = run_operations_evaluation(company=company, actor="test:offline")

    assert evaluation.status == OperationsEvaluationRun.Status.PASSED
    assert evaluation.cases_total == len(OFFLINE_SCENARIOS) == 6
    assert evaluation.cases_passed == 6
    assert evaluation.unauthorized_external_actions == 0


def test_live_operations_suite_requires_human_review(company, successful_openai):
    evaluation = run_operations_evaluation(company=company, actor="test:live", live=True)

    assert evaluation.status == OperationsEvaluationRun.Status.NEEDS_REVIEW
    assert evaluation.technical_gate_passed
    assert evaluation.cases_total == len(LIVE_SCENARIOS) == 6
    assert evaluation.cases_passed == 6
    assert evaluation.evidence_validity_percent == 100
    assert evaluation.consistency_percent == 100
    assert evaluation.total_input_tokens == 540
    assert evaluation.total_output_tokens == 108
    assert AuditEvent.objects.filter(event_type="live-operations-evaluation-completed").exists()


def test_operations_human_gate_requires_note(company, successful_openai, operator):
    evaluation = run_operations_evaluation(company=company, actor="test:live", live=True)

    with pytest.raises(ValidationError, match="review note"):
        decide_operations_evaluation(
            evaluation=evaluation,
            decision=OperationsEvaluationRun.Status.PASSED,
            decided_by=operator,
            note="",
        )

    decide_operations_evaluation(
        evaluation=evaluation,
        decision=OperationsEvaluationRun.Status.PASSED,
        decided_by=operator,
        note="Cycle-grounded improvements are useful and remain internal drafts.",
    )
    evaluation.refresh_from_db()
    assert evaluation.status == OperationsEvaluationRun.Status.PASSED
    assert evaluation.human_review_completed
