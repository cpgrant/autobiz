from datetime import date

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.operations import cycle_services
from apps.operations.cycle_services import next_operating_date, run_daily_cycle
from apps.operations.models import (
    ActionProposal,
    Approval,
    AuditEvent,
    Company,
    OperatingCycle,
    WeeklyReport,
    WorkItem,
)
from apps.operations.services import can_execute_action, decide_approval


@pytest.fixture
def company(db):
    call_command("load_customer_zero", verbosity=0)
    return Company.objects.get(key="autobiz")


def test_daily_cycle_reads_state_simulates_internal_work_and_writes_reports(company):
    result = run_daily_cycle(company=company, actor="test:cycle-runner")

    assert result.cycle.operating_date == date(2026, 8, 2)
    assert result.cycle.status == OperatingCycle.Status.COMPLETED
    assert result.internal_actions_simulated == 1
    assert "State read:" in str(result.cycle.report)
    assert "Highest-priority work:" in str(result.cycle.report)
    assert "External execution remained disabled" in str(result.cycle.report)
    assert result.weekly_report.week_start == date(2026, 7, 27)
    assert result.weekly_report.cycle_count == 2
    assert "Unauthorized external actions: 0" in str(result.weekly_report.report)
    assert WorkItem.objects.get(key="daily-state-review-2026-08-02").status == WorkItem.Status.DONE
    assert (
        ActionProposal.objects.get(key="daily-state-review-2026-08-02").status
        == ActionProposal.Status.SIMULATED
    )
    for event_type in [
        "daily-cycle-started",
        "company-state-read",
        "next-actions-selected",
        "internal-action-simulated",
        "weekly-report-updated",
        "daily-cycle-completed",
    ]:
        assert AuditEvent.objects.filter(event_type=event_type).exists()


def test_completed_cycle_is_idempotent(company):
    first = run_daily_cycle(
        company=company,
        actor="test:cycle-runner",
        operating_date=date(2026, 8, 2),
    )
    counts = (
        OperatingCycle.objects.count(),
        WorkItem.objects.count(),
        ActionProposal.objects.count(),
        Approval.objects.count(),
        AuditEvent.objects.filter(event_type="daily-cycle-completed").count(),
        WeeklyReport.objects.count(),
    )

    second = run_daily_cycle(
        company=company,
        actor="test:cycle-runner",
        operating_date=date(2026, 8, 2),
    )

    assert first.created
    assert not second.created
    assert counts == (
        OperatingCycle.objects.count(),
        WorkItem.objects.count(),
        ActionProposal.objects.count(),
        Approval.objects.count(),
        AuditEvent.objects.filter(event_type="daily-cycle-completed").count(),
        WeeklyReport.objects.count(),
    )


def test_cycle_routes_new_consequential_action_after_prior_decision(company, operator):
    initial = Approval.objects.get(status=Approval.Status.PENDING)
    decide_approval(
        approval=initial,
        decision=Approval.Status.APPROVED,
        decided_by=operator,
        note="Clear the seeded synthetic request.",
    )

    result = run_daily_cycle(company=company, actor="test:cycle-runner")

    assert result.approvals_requested == 1
    proposal = ActionProposal.objects.get(key="daily-follow-up-2026-08-02")
    assert proposal.status == ActionProposal.Status.AWAITING_APPROVAL
    assert proposal.approval is not None
    assert proposal.approval.status == Approval.Status.PENDING
    assert not proposal.executor_available
    assert not company.external_execution_enabled
    assert not can_execute_action(company=company, proposal=proposal)
    assert AuditEvent.objects.filter(event_type="approval-requested").exists()


def test_pending_approval_prevents_duplicate_consequential_request(company):
    result = run_daily_cycle(company=company, actor="test:cycle-runner")

    assert result.approvals_requested == 0
    assert Approval.objects.filter(status=Approval.Status.PENDING).count() == 1
    assert not ActionProposal.objects.filter(key="daily-follow-up-2026-08-02").exists()


def test_failed_cycle_is_recorded_and_same_date_can_recover(company, monkeypatch):
    original = cycle_services._create_internal_simulation

    def fail_safely(*, company, cycle):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(cycle_services, "_create_internal_simulation", fail_safely)
    with pytest.raises(RuntimeError, match="synthetic failure"):
        run_daily_cycle(company=company, actor="test:failure")

    failed = OperatingCycle.objects.get(operating_date=date(2026, 8, 2))
    assert failed.status == OperatingCycle.Status.FAILED
    assert next_operating_date(company) == date(2026, 8, 2)
    assert AuditEvent.objects.filter(event_type="daily-cycle-failed").exists()

    monkeypatch.setattr(cycle_services, "_create_internal_simulation", original)
    recovered = run_daily_cycle(company=company, actor="test:recovery")
    assert recovered.cycle.status == OperatingCycle.Status.COMPLETED
    assert OperatingCycle.objects.filter(operating_date=date(2026, 8, 2)).count() == 1


def test_operator_can_run_next_synthetic_day(client, company, operator):
    operator.is_staff = True
    operator.save(update_fields=["is_staff"])
    client.force_login(operator)

    response = client.post(reverse("operator-run-cycle"))

    assert response.status_code == 302
    assert OperatingCycle.objects.filter(operating_date=date(2026, 8, 2)).exists()
    page = client.get(reverse("operator-dashboard")).content.decode()
    assert "Run next synthetic day" in page
    assert "Daily operating reports" in page
    assert "Weekly operating reports" in page
    assert "2026-08-02" in page
