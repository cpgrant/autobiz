from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import (
    ActionProposal,
    Approval,
    AuditEvent,
    Company,
    Engagement,
    Goal,
    OperatingCycle,
    Opportunity,
    WeeklyReport,
    WorkflowRun,
    WorkItem,
)
from .services import authority_rule_for, refresh_company_state


@dataclass(frozen=True)
class DailyCycleResult:
    cycle: OperatingCycle
    weekly_report: WeeklyReport
    created: bool
    selected_work_count: int
    proposals_created: int
    internal_actions_simulated: int
    approvals_requested: int


def next_operating_date(company: Company) -> date:
    latest = company.operating_cycles.aggregate(latest=Max("operating_date"))["latest"]
    if latest is None:
        return date(2026, 8, 1)
    latest_cycle = company.operating_cycles.get(operating_date=latest)
    if latest_cycle.status == OperatingCycle.Status.FAILED:
        return latest
    return latest + timedelta(days=1)


def _audit(*, company: Company, event_type: str, actor: str, payload: dict) -> AuditEvent:
    return AuditEvent.objects.create(
        event_type=event_type,
        actor=actor,
        payload={"company_id": str(company.pk), "synthetic": True, **payload},
    )


def _company_snapshot(company: Company) -> dict[str, int | str]:
    return {
        "active_goals": company.goals.filter(status=Goal.Status.ACTIVE).count(),
        "open_opportunities": company.opportunities.exclude(
            stage__in=[Opportunity.Stage.WON, Opportunity.Stage.LOST]
        ).count(),
        "active_work_items": company.work_items.exclude(status=WorkItem.Status.DONE).count(),
        "financial_entries": company.financial_entries.count(),
        "open_risks": company.risks.filter(status="open").count(),
        "prior_completed_cycles": company.operating_cycles.filter(
            status=OperatingCycle.Status.COMPLETED
        ).count(),
    }


def _create_internal_simulation(
    *, company: Company, cycle: OperatingCycle
) -> tuple[WorkItem, ActionProposal, bool]:
    suffix = cycle.operating_date.isoformat()
    work_item, _ = WorkItem.objects.get_or_create(
        company=company,
        key=f"daily-state-review-{suffix}",
        defaults={
            "title": f"Review company state for {suffix}",
            "function": WorkItem.Function.OPERATIONS,
            "status": WorkItem.Status.READY,
            "priority": 1,
            "is_synthetic": True,
        },
    )
    rule = authority_rule_for("create-simulated-task")
    proposal, created = ActionProposal.objects.get_or_create(
        company=company,
        key=f"daily-state-review-{suffix}",
        defaults={
            "operating_cycle": cycle,
            "work_item": work_item,
            "action_type": "create-simulated-task",
            "title": f"Complete the internal state review for {suffix}",
            "authority_level": rule.level,
            "status": ActionProposal.Status.PROPOSED,
            "requires_approval": rule.requires_approval,
            "is_external": rule.external,
            "executor_available": rule.executor_available,
            "is_synthetic": True,
        },
    )
    if proposal.status != ActionProposal.Status.SIMULATED:
        proposal.status = ActionProposal.Status.SIMULATED
        proposal.outcome = {
            "result": "Company state reviewed using deterministic local records.",
            "reversible": True,
            "synthetic": True,
        }
        proposal.save(update_fields=["status", "outcome", "updated_at"])
    if work_item.status != WorkItem.Status.DONE:
        work_item.status = WorkItem.Status.DONE
        work_item.save(update_fields=["status", "updated_at"])
    return work_item, proposal, created


def _route_consequential_action(
    *, company: Company, cycle: OperatingCycle
) -> tuple[ActionProposal | None, bool]:
    pending_exists = Approval.objects.filter(
        status=Approval.Status.PENDING,
        workflow_run__engagement__customer__company=company,
        action_type="send-communication",
    ).exists()
    if pending_exists:
        return None, False

    opportunity = (
        company.opportunities.exclude(stage__in=[Opportunity.Stage.WON, Opportunity.Stage.LOST])
        .select_related("customer", "product")
        .order_by("-probability_percent", "-estimated_value_eur", "key")
        .first()
    )
    pilot = (
        Engagement.objects.filter(
            customer__company=company,
            customer__status="pilot",
            is_synthetic=True,
        )
        .select_related("customer")
        .first()
    )
    if opportunity is None or pilot is None:
        return None, False

    suffix = cycle.operating_date.isoformat()
    work_item, _ = WorkItem.objects.get_or_create(
        company=company,
        key=f"daily-follow-up-{suffix}",
        defaults={
            "title": f"Draft follow-up for {opportunity.customer.name}",
            "function": WorkItem.Function.GROWTH,
            "status": WorkItem.Status.BLOCKED,
            "priority": 1,
            "requires_approval": True,
            "is_synthetic": True,
        },
    )
    workflow_run, _ = WorkflowRun.objects.get_or_create(
        engagement=pilot,
        workflow_key=f"daily-follow-up-{suffix}",
        defaults={
            "status": WorkflowRun.Status.AWAITING_APPROVAL,
            "input_data": {
                "opportunity_id": str(opportunity.pk),
                "operating_cycle_id": str(cycle.pk),
                "synthetic": True,
            },
        },
    )
    approval, approval_created = Approval.objects.get_or_create(
        workflow_run=workflow_run,
        action_type="send-communication",
        defaults={
            "request_payload": {
                "recipient": opportunity.customer.primary_email,
                "subject": f"Synthetic follow-up: {opportunity.product.name}",
                "opportunity_id": str(opportunity.pk),
                "synthetic": True,
            }
        },
    )
    rule = authority_rule_for("send-communication")
    proposal, _ = ActionProposal.objects.get_or_create(
        company=company,
        key=f"daily-follow-up-{suffix}",
        defaults={
            "operating_cycle": cycle,
            "work_item": work_item,
            "approval": approval,
            "action_type": "send-communication",
            "title": f"Send synthetic follow-up to {opportunity.customer.name}",
            "authority_level": rule.level,
            "status": ActionProposal.Status.AWAITING_APPROVAL,
            "requires_approval": rule.requires_approval,
            "is_external": rule.external,
            "executor_available": rule.executor_available,
            "is_synthetic": True,
        },
    )
    return proposal, approval_created


def _weekly_report(company: Company, operating_date: date) -> WeeklyReport:
    week_start = operating_date - timedelta(days=operating_date.weekday())
    week_end = week_start + timedelta(days=6)
    cycles = company.operating_cycles.filter(
        operating_date__range=(week_start, week_end),
        status=OperatingCycle.Status.COMPLETED,
    ).order_by("operating_date")
    dates = ", ".join(cycle.operating_date.isoformat() for cycle in cycles)
    simulated = ActionProposal.objects.filter(
        company=company,
        operating_cycle__in=cycles,
        status=ActionProposal.Status.SIMULATED,
    ).count()
    approvals = ActionProposal.objects.filter(
        company=company,
        operating_cycle__in=cycles,
        approval__isnull=False,
    ).count()
    report_text = (
        f"# Weekly operating report · {week_start.isoformat()}\n\n"
        f"Completed cycles: {cycles.count()} ({dates or 'none'}).\n"
        f"Bounded internal simulations: {simulated}.\n"
        f"Approval requests created: {approvals}.\n"
        f"Unauthorized external actions: 0.\n"
        "External execution remained disabled."
    )
    report, _ = WeeklyReport.objects.update_or_create(
        company=company,
        week_start=week_start,
        defaults={
            "cycle_count": cycles.count(),
            "report": report_text,
            "is_synthetic": True,
        },
    )
    return report


def _daily_report(
    *,
    cycle: OperatingCycle,
    snapshot: dict[str, int | str],
    selected_work: list[WorkItem],
    approval_requested: bool,
) -> str:
    selected = ", ".join(str(item.title) for item in selected_work) or "No open work"
    approval_line = (
        "One synthetic communication proposal was routed to human approval."
        if approval_requested
        else "No new approval was created; an existing request may still be pending."
    )
    return (
        f"# Daily operating report · {cycle.operating_date.isoformat()}\n\n"
        f"State read: {snapshot['active_goals']} active goals, "
        f"{snapshot['open_opportunities']} open opportunities, "
        f"{snapshot['active_work_items']} active work items, "
        f"{snapshot['financial_entries']} financial entries, and "
        f"{snapshot['open_risks']} open risks.\n\n"
        f"Highest-priority work: {selected}.\n\n"
        "Completed one reversible internal state-review simulation. "
        f"{approval_line}\n\n"
        "External execution remained disabled; unauthorized external actions: 0."
    )


def run_daily_cycle(
    *, company: Company, actor: str, operating_date: date | None = None
) -> DailyCycleResult:
    run_date = operating_date or next_operating_date(company)
    cycle, created = OperatingCycle.objects.get_or_create(
        company=company,
        operating_date=run_date,
        defaults={"status": OperatingCycle.Status.PLANNED, "is_synthetic": True},
    )
    if cycle.status == OperatingCycle.Status.COMPLETED:
        weekly = _weekly_report(company, run_date)
        return DailyCycleResult(cycle, weekly, False, 0, 0, 0, 0)

    try:
        with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
            cycle = OperatingCycle.objects.select_for_update().get(pk=cycle.pk)
            cycle.status = OperatingCycle.Status.RUNNING
            cycle.report = ""
            cycle.save(update_fields=["status", "report", "updated_at"])
            _audit(
                company=company,
                event_type="daily-cycle-started",
                actor=actor,
                payload={"operating_cycle_id": str(cycle.pk), "date": run_date.isoformat()},
            )

            refresh_company_state(company=company, actor=actor)
            snapshot = _company_snapshot(company)
            _audit(
                company=company,
                event_type="company-state-read",
                actor=actor,
                payload={"operating_cycle_id": str(cycle.pk), "state": snapshot},
            )
            selected_work = list(
                company.work_items.exclude(status=WorkItem.Status.DONE).order_by(
                    "priority", "created_at"
                )[:3]
            )
            _audit(
                company=company,
                event_type="next-actions-selected",
                actor=actor,
                payload={
                    "operating_cycle_id": str(cycle.pk),
                    "work_item_ids": [str(item.pk) for item in selected_work],
                },
            )

            _, internal_proposal, proposal_created = _create_internal_simulation(
                company=company, cycle=cycle
            )
            _audit(
                company=company,
                event_type="internal-action-simulated",
                actor=actor,
                payload={
                    "operating_cycle_id": str(cycle.pk),
                    "action_proposal_id": str(internal_proposal.pk),
                    "reversible": True,
                },
            )
            approval_proposal, approval_created = _route_consequential_action(
                company=company, cycle=cycle
            )
            if approval_created and approval_proposal is not None:
                _audit(
                    company=company,
                    event_type="approval-requested",
                    actor=actor,
                    payload={
                        "operating_cycle_id": str(cycle.pk),
                        "action_proposal_id": str(approval_proposal.pk),
                        "approval_id": str(approval_proposal.approval_id),
                    },
                )

            cycle.report = _daily_report(
                cycle=cycle,
                snapshot=snapshot,
                selected_work=selected_work,
                approval_requested=approval_created,
            )
            cycle.status = OperatingCycle.Status.COMPLETED
            cycle.save(update_fields=["status", "report", "updated_at"])
            completed_count = company.operating_cycles.filter(
                status=OperatingCycle.Status.COMPLETED
            ).count()
            company.goals.filter(key="complete-daily-cycle").update(
                current_value=Decimal(completed_count)
            )
            refresh_company_state(company=company, actor=actor)
            weekly = _weekly_report(company, run_date)
            _audit(
                company=company,
                event_type="weekly-report-updated",
                actor=actor,
                payload={"weekly_report_id": str(weekly.pk), "week_start": str(weekly.week_start)},
            )
            _audit(
                company=company,
                event_type="daily-cycle-completed",
                actor=actor,
                payload={
                    "operating_cycle_id": str(cycle.pk),
                    "date": run_date.isoformat(),
                    "completed_at": timezone.now().isoformat(),
                    "external_execution_enabled": company.external_execution_enabled,
                },
            )
            return DailyCycleResult(
                cycle=cycle,
                weekly_report=weekly,
                created=created,
                selected_work_count=len(selected_work),
                proposals_created=int(proposal_created) + int(approval_proposal is not None),
                internal_actions_simulated=1,
                approvals_requested=int(approval_created),
            )
    except Exception as error:
        OperatingCycle.objects.filter(pk=cycle.pk).update(
            status=OperatingCycle.Status.FAILED,
            report=f"Cycle failed safely: {type(error).__name__}.",
        )
        _audit(
            company=company,
            event_type="daily-cycle-failed",
            actor=actor,
            payload={
                "operating_cycle_id": str(cycle.pk),
                "date": run_date.isoformat(),
                "error_type": type(error).__name__,
            },
        )
        raise
