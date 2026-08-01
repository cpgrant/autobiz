from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.operations.models import (
    ActionProposal,
    Approval,
    AuditEvent,
    Company,
    Customer,
    Engagement,
    FinancialEntry,
    Goal,
    Metric,
    OperatingCycle,
    Opportunity,
    Product,
    Risk,
    WorkflowRun,
    WorkItem,
)
from apps.operations.services import authority_rule_for


class Command(BaseCommand):
    help = "Load the idempotent, clearly marked Customer Zero synthetic scenario."

    @transaction.atomic
    def handle(self, *args, **options):
        company, _ = Company.objects.update_or_create(
            key="autobiz",
            defaults={
                "name": "Autobiz",
                "mission": (
                    "Operate a controlled agent-driven company using safe, measurable "
                    "synthetic workflows."
                ),
                "is_synthetic": True,
                "external_execution_enabled": False,
            },
        )

        services = {}
        for key, name, outcome in [
            ("establish", "Establish", "Create a controlled operating foundation."),
            ("operate", "Operate", "Run a visible, repeatable operating rhythm."),
            ("improve", "Improve", "Measure results and improve the constrained workflow."),
        ]:
            services[key], _ = Product.objects.update_or_create(
                key=key,
                defaults={
                    "company": company,
                    "name": name,
                    "status": Product.Status.PILOT,
                    "promised_outcome": outcome,
                    "is_synthetic": True,
                },
            )

        prospects = []
        for number in range(1, 11):
            prospect, _ = Customer.objects.update_or_create(
                company=company,
                name=f"Synthetic Prospect {number:02d}",
                defaults={
                    "status": Customer.Status.PROSPECT,
                    "primary_email": f"prospect-{number:02d}@example.invalid",
                    "notes": "SYNTHETIC — Customer Zero simulation record.",
                    "is_synthetic": True,
                },
            )
            prospects.append(prospect)

        customer, _ = Customer.objects.update_or_create(
            company=company,
            name="Synthetic Customer Northstar",
            defaults={
                "status": Customer.Status.ACTIVE,
                "primary_email": "northstar@example.invalid",
                "notes": "SYNTHETIC — example customer, not a real commercial relationship.",
                "is_synthetic": True,
            },
        )
        pilot_party, _ = Customer.objects.update_or_create(
            company=company,
            name="Autobiz Internal Pilot",
            defaults={
                "status": Customer.Status.PILOT,
                "notes": "SYNTHETIC — internal Customer Zero pilot.",
                "is_synthetic": True,
            },
        )
        pilot, _ = Engagement.objects.update_or_create(
            customer=pilot_party,
            product=services["operate"],
            defaults={
                "status": Engagement.Status.PILOT,
                "starts_on": date(2026, 8, 1),
                "is_synthetic": True,
            },
        )
        Engagement.objects.update_or_create(
            customer=customer,
            product=services["establish"],
            defaults={
                "status": Engagement.Status.ACTIVE,
                "starts_on": date(2026, 7, 28),
                "is_synthetic": True,
            },
        )

        for key, prospect, product, stage, value, probability in [
            ("atlas-establish", prospects[0], services["establish"], "qualified", 1800, 55),
            ("beacon-operate", prospects[1], services["operate"], "discovered", 2400, 30),
            ("cedar-improve", prospects[2], services["improve"], "proposed", 3200, 70),
        ]:
            Opportunity.objects.update_or_create(
                company=company,
                key=key,
                defaults={
                    "customer": prospect,
                    "product": product,
                    "stage": stage,
                    "estimated_value_eur": Decimal(value),
                    "probability_percent": probability,
                    "is_synthetic": True,
                },
            )

        Goal.objects.update_or_create(
            company=company,
            key="complete-daily-cycle",
            defaults={
                "name": "Complete controlled daily operating cycles",
                "target_value": 10,
                "current_value": 1,
                "unit": "cycles",
                "due_on": date(2026, 8, 21),
                "is_synthetic": True,
            },
        )
        for key, name, value, target, unit in [
            ("cycle-completion", "Daily cycle completion", 1, 10, "cycles"),
            ("approval-rate", "Approval rate", 0, 80, "percent"),
            ("unauthorized-actions", "Unauthorized external actions", 0, 0, "actions"),
            ("pipeline-value", "Weighted pipeline value", 3900, 5000, "EUR"),
        ]:
            Metric.objects.update_or_create(
                company=company,
                key=key,
                defaults={
                    "name": name,
                    "value": Decimal(value),
                    "target_value": Decimal(target),
                    "unit": unit,
                    "is_synthetic": True,
                },
            )

        work_items = {}
        for key, title, function, priority, status, approval in [
            ("review-goals", "Review goals and company state", "direction", 1, "ready", False),
            ("qualify-atlas", "Qualify the Atlas opportunity", "growth", 2, "proposed", False),
            (
                "pilot-checklist",
                "Complete internal pilot checklist",
                "delivery",
                1,
                "in_progress",
                False,
            ),
            ("cash-forecast", "Refresh the synthetic cash forecast", "finance", 2, "ready", False),
            ("risk-review", "Review open exceptions", "operations", 1, "ready", False),
            ("draft-follow-up", "Draft prospect follow-up", "growth", 3, "blocked", True),
        ]:
            work_items[key], _ = WorkItem.objects.update_or_create(
                company=company,
                key=key,
                defaults={
                    "title": title,
                    "function": function,
                    "priority": priority,
                    "status": status,
                    "requires_approval": approval,
                    "is_synthetic": True,
                },
            )

        for key, entry_type, description, amount, occurred_on in [
            ("opening-cash", "cash", "Synthetic opening cash", 10000, date(2026, 8, 1)),
            (
                "pilot-revenue",
                "revenue",
                "Synthetic Establish pilot revenue",
                1200,
                date(2026, 8, 1),
            ),
            ("software-cost", "cost", "Synthetic software and model cost", 185, date(2026, 8, 1)),
        ]:
            FinancialEntry.objects.update_or_create(
                company=company,
                key=key,
                defaults={
                    "entry_type": entry_type,
                    "description": description,
                    "amount_eur": Decimal(amount),
                    "occurred_on": occurred_on,
                    "is_synthetic": True,
                },
            )

        for key, title, severity, mitigation in [
            (
                "external-action-disabled",
                "External action requested while all external executors are disabled",
                "high",
                "Keep proposal blocked and route it to human review.",
            ),
            (
                "missing-quality-sample",
                "Pilot delivery has not yet received a quality sample",
                "medium",
                "Add a deterministic quality checklist before cycle completion.",
            ),
        ]:
            Risk.objects.update_or_create(
                company=company,
                key=key,
                defaults={
                    "title": title,
                    "severity": severity,
                    "status": Risk.Status.OPEN,
                    "mitigation": mitigation,
                    "is_synthetic": True,
                },
            )

        cycle, _ = OperatingCycle.objects.update_or_create(
            company=company,
            operating_date=date(2026, 8, 1),
            defaults={
                "status": OperatingCycle.Status.COMPLETED,
                "report": (
                    "Day 0 loaded. Internal planning is ready; one external action is "
                    "blocked pending approval and remains non-executable."
                ),
                "is_synthetic": True,
            },
        )
        WorkflowRun.objects.update_or_create(
            engagement=pilot,
            workflow_key="customer-zero-day-0",
            defaults={
                "status": WorkflowRun.Status.COMPLETED,
                "output_data": {"operating_cycle_id": str(cycle.pk), "synthetic": True},
            },
        )
        approval_run, _ = WorkflowRun.objects.get_or_create(
            engagement=pilot,
            workflow_key="synthetic-external-follow-up",
            defaults={
                "status": WorkflowRun.Status.AWAITING_APPROVAL,
                "input_data": {
                    "recipient": "prospect-01@example.invalid",
                    "synthetic": True,
                },
            },
        )
        approval, _ = Approval.objects.get_or_create(
            workflow_run=approval_run,
            action_type="send-communication",
            defaults={
                "request_payload": {
                    "recipient": "prospect-01@example.invalid",
                    "subject": "Synthetic Atlas follow-up",
                    "synthetic": True,
                }
            },
        )

        for key, action_type, title, work_key, status in [
            (
                "create-risk-review-task",
                "create-simulated-task",
                "Create an internal risk-review task",
                "risk-review",
                "simulated",
            ),
            (
                "send-atlas-follow-up",
                "send-communication",
                "Send synthetic Atlas follow-up",
                "draft-follow-up",
                "awaiting_approval",
            ),
            (
                "access-prospect-crm",
                "access-external-system",
                "Access an external prospect CRM",
                "qualify-atlas",
                "blocked",
            ),
        ]:
            rule = authority_rule_for(action_type)
            proposal, _ = ActionProposal.objects.update_or_create(
                company=company,
                key=key,
                defaults={
                    "operating_cycle": cycle,
                    "work_item": work_items[work_key],
                    "action_type": action_type,
                    "title": title,
                    "authority_level": rule.level,
                    "status": status,
                    "requires_approval": rule.requires_approval,
                    "is_external": rule.external,
                    "executor_available": rule.executor_available,
                    "outcome": {"synthetic": True} if status == "simulated" else {},
                    "is_synthetic": True,
                },
            )
            if key == "send-atlas-follow-up":
                proposal.approval = approval
                proposal.status = {
                    Approval.Status.PENDING: ActionProposal.Status.AWAITING_APPROVAL,
                    Approval.Status.APPROVED: ActionProposal.Status.AUTHORIZED,
                    Approval.Status.REJECTED: ActionProposal.Status.REJECTED,
                    Approval.Status.EXPIRED: ActionProposal.Status.BLOCKED,
                }[approval.status]
                proposal.save(update_fields=["approval", "status", "updated_at"])
            AuditEvent.objects.get_or_create(
                event_type=f"synthetic-proposal-{key}",
                actor="system:customer-zero-loader",
                defaults={
                    "payload": {
                        "action_proposal_id": str(proposal.pk),
                        "action_type": action_type,
                        "synthetic": True,
                    }
                },
            )

        self.stdout.write(self.style.SUCCESS("Customer Zero synthetic scenario is ready."))
