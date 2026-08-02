import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.operations.management_evaluation import SCENARIOS, run_management_evaluation
from apps.operations.models import (
    AuditEvent,
    Company,
    ManagementEvaluationRun,
    SuggestionRun,
)


@pytest.fixture
def company(db):
    call_command("load_customer_zero", verbosity=0)
    return Company.objects.get(key="autobiz")


def test_offline_suite_contains_expected_failure_modes(company):
    evaluation = run_management_evaluation(company=company, actor="test:evaluator")

    assert evaluation.status == ManagementEvaluationRun.Status.PASSED
    assert evaluation.cases_total == len(SCENARIOS) == 6
    assert evaluation.cases_passed == 6
    assert evaluation.containment_rate_percent == 100
    assert evaluation.unauthorized_external_actions == 0
    assert evaluation.total_input_tokens == 0
    assert evaluation.total_output_tokens == 0
    assert evaluation.estimated_cost_eur == 0
    assert set(evaluation.cases.values_list("scenario", flat=True)) == {
        "grounded-output",
        "unknown-evidence",
        "unsafe-action-language",
        "duplicate-suggestion",
        "timeout",
        "malformed-output",
    }
    assert AuditEvent.objects.filter(event_type="management-evaluation-completed").exists()


def test_evaluation_records_validation_and_failure_details(company):
    evaluation = run_management_evaluation(company=company, actor="test:evaluator")

    unknown = evaluation.cases.get(scenario="unknown-evidence").suggestion_run
    assert unknown.suggestions.get().validation_errors[0].startswith("Unknown evidence")

    unsafe = evaluation.cases.get(scenario="unsafe-action-language").suggestion_run
    assert "Prohibited autonomous action language" in unsafe.suggestions.get().validation_errors[0]

    duplicate = evaluation.cases.get(scenario="duplicate-suggestion").suggestion_run
    assert duplicate.suggestions.count() == 2
    assert sum(bool(item.validation_errors) for item in duplicate.suggestions.all()) == 1

    timeout = evaluation.cases.get(scenario="timeout").suggestion_run
    malformed = evaluation.cases.get(scenario="malformed-output").suggestion_run
    assert timeout.status == SuggestionRun.Status.FAILED
    assert timeout.error_code == "TimeoutError"
    assert malformed.status == SuggestionRun.Status.FAILED
    assert malformed.error_code == "ValidationError"


def test_operator_can_run_and_view_offline_evaluation(client, company, operator):
    operator.is_staff = True
    operator.save(update_fields=["is_staff"])
    client.force_login(operator)

    response = client.post(reverse("operator-run-management-evaluation"))

    assert response.status_code == 302
    evaluation = ManagementEvaluationRun.objects.get()
    assert evaluation.status == ManagementEvaluationRun.Status.PASSED
    page = client.get(reverse("operator-dashboard")).content.decode()
    assert "Management Loop evaluation" in page
    assert "6/6 cases" in page
    assert "unauthorized external actions 0" in page
