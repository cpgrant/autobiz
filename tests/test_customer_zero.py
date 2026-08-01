from django.core.management import call_command
from django.urls import reverse

from apps.operations.models import (
    ActionProposal,
    Approval,
    Company,
    Customer,
    FinancialEntry,
    Opportunity,
    Product,
)
from apps.operations.services import authority_rule_for, can_execute_action


def load_scenario():
    call_command("load_customer_zero", verbosity=0)


def test_customer_zero_loader_is_idempotent(db):
    load_scenario()
    first_counts = (
        Company.objects.count(),
        Customer.objects.count(),
        Product.objects.count(),
        Opportunity.objects.count(),
        FinancialEntry.objects.count(),
        ActionProposal.objects.count(),
        Approval.objects.count(),
    )

    load_scenario()

    assert first_counts == (1, 12, 3, 3, 3, 3, 1)
    assert first_counts == (
        Company.objects.count(),
        Customer.objects.count(),
        Product.objects.count(),
        Opportunity.objects.count(),
        FinancialEntry.objects.count(),
        ActionProposal.objects.count(),
        Approval.objects.count(),
    )


def test_customer_zero_records_are_explicitly_synthetic(db):
    load_scenario()

    assert Company.objects.filter(is_synthetic=False).count() == 0
    assert Customer.objects.filter(is_synthetic=False).count() == 0
    assert Product.objects.filter(is_synthetic=False).count() == 0
    assert Opportunity.objects.filter(is_synthetic=False).count() == 0
    assert ActionProposal.objects.filter(is_synthetic=False).count() == 0


def test_external_and_unknown_actions_fail_closed(db):
    load_scenario()
    company = Company.objects.get(key="autobiz")
    communication = ActionProposal.objects.get(key="send-atlas-follow-up")

    assert not company.external_execution_enabled
    assert communication.requires_approval
    assert not communication.executor_available
    assert not can_execute_action(company=company, proposal=communication)
    assert (
        authority_rule_for("unrecognized-action").level == ActionProposal.AuthorityLevel.PROHIBITED
    )


def test_bounded_internal_simulation_is_executable(db):
    load_scenario()
    company = Company.objects.get(key="autobiz")
    proposal = ActionProposal.objects.get(key="create-risk-review-task")

    assert can_execute_action(company=company, proposal=proposal)


def test_company_status_shows_synthetic_operating_state(client, db):
    load_scenario()

    response = client.get(reverse("company-status"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Synthetic data only" in content
    assert "Priority work" in content
    assert "Deterministic metrics" in content
    assert "Action control" in content
    assert "External action requested" in content
