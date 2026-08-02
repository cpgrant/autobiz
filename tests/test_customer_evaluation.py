import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from apps.operations.ai_providers import CustomerProviderResult, OpenAIResponsesProvider
from apps.operations.ai_schemas import CustomerLoopOutput
from apps.operations.customer_evaluation import (
    LIVE_SCENARIOS,
    OFFLINE_SCENARIOS,
    decide_customer_evaluation,
    run_customer_evaluation,
)
from apps.operations.models import Company, CustomerEvaluationRun, OperationsEvaluationRun
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
        customer_name="Synthetic Evaluation Customer",
        email="evaluation@example.invalid",
        request_text="Please acknowledge this synthetic request.",
        desired_outcome="A safe draft.",
    )
    return company


@pytest.fixture
def successful_openai(monkeypatch):
    def respond(self, *, snapshot):
        request = snapshot["customer_requests"][0]
        return CustomerProviderResult(
            output=CustomerLoopOutput.model_validate(
                {
                    "summary": "Safe synthetic draft.",
                    "drafts": [
                        {
                            "subject": "Synthetic request acknowledgement",
                            "body": "Thank you. Your request is recorded for internal review.",
                            "intent": "acknowledge",
                            "escalation_reason": None,
                            "evidence": [
                                {
                                    "record_type": "customer_request",
                                    "record_id": request["id"],
                                }
                            ],
                        }
                    ],
                }
            ),
            provider="openai",
            model=self.model,
            latency_ms=20,
            input_tokens=80,
            output_tokens=16,
        )

    monkeypatch.setattr(OpenAIResponsesProvider, "customer_drafts", respond)


def test_offline_customer_suite_passes(company):
    evaluation = run_customer_evaluation(company=company, actor="test:offline")
    assert evaluation.status == CustomerEvaluationRun.Status.PASSED
    assert evaluation.cases_total == len(OFFLINE_SCENARIOS) == 7
    assert evaluation.cases_passed == 7
    assert evaluation.unauthorized_external_actions == 0


def test_safe_privacy_refusal_is_not_blocked():
    from apps.operations.customer_loop import _validate_customer_safety

    assert not _validate_customer_safety(
        "Privacy reminder", "Please do not provide passwords or payment-card details."
    )
    assert _validate_customer_safety("Sensitive request", "Please reply with your password.")


def test_live_customer_suite_requires_human_review(company, successful_openai):
    evaluation = run_customer_evaluation(company=company, actor="test:live", live=True)
    assert evaluation.status == CustomerEvaluationRun.Status.NEEDS_REVIEW
    assert evaluation.cases_total == len(LIVE_SCENARIOS) == 6
    assert evaluation.cases_passed == 6
    assert evaluation.evidence_validity_percent == 100
    assert evaluation.consistency_percent == 100
    assert evaluation.unauthorized_external_actions == 0


def test_customer_human_gate_requires_note(company, successful_openai, operator):
    evaluation = run_customer_evaluation(company=company, actor="test:live", live=True)
    with pytest.raises(ValidationError, match="review note"):
        decide_customer_evaluation(
            evaluation=evaluation,
            decision=CustomerEvaluationRun.Status.PASSED,
            decided_by=operator,
            note="",
        )
