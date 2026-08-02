from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from time import monotonic

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .ai_providers import CustomerAIProvider
from .models import (
    AuditEvent,
    Company,
    CustomerDraft,
    CustomerDraftRun,
    CustomerRequest,
    OperationsEvaluationRun,
)


@dataclass(frozen=True)
class CustomerLoopResult:
    run: CustomerDraftRun
    drafts_created: int


def customer_snapshot(company: Company, customer_request: CustomerRequest | None = None) -> dict:
    customer_request = (
        customer_request or company.customer_requests.filter(is_synthetic=True).first()
    )
    if customer_request is None:
        raise ValidationError("At least one synthetic customer request is required.")

    def value(item):
        return str(item) if isinstance(item, (Decimal, date)) else item

    def record(item, record_type: str, fields: tuple[str, ...]) -> dict:
        return {
            "record_type": record_type,
            "id": str(item.pk),
            **{field: value(getattr(item, field)) for field in fields},
        }

    snapshot = {
        "company": {"id": str(company.pk), "name": company.name},
        "customer_requests": [
            record(
                customer_request,
                "customer_request",
                ("request_text", "desired_outcome", "status"),
            )
        ],
        "offers": [],
        "engagements": [],
        "deliverables": [],
        "external_sending_enabled": False,
    }
    if hasattr(customer_request, "offer"):
        snapshot["offers"].append(
            record(customer_request.offer, "offer", ("title", "scope", "price_eur", "status"))
        )
    if customer_request.engagement_id:
        snapshot["engagements"].append(
            record(customer_request.engagement, "engagement", ("status", "starts_on", "ends_on"))
        )
    snapshot["deliverables"] = [
        record(item, "deliverable", ("title", "version", "status"))
        for item in customer_request.deliverables.all()[:3]
    ]
    return snapshot


def _validate_customer_evidence(snapshot: dict, evidence: list[dict]) -> list[str]:
    available = {
        (record["record_type"], record["id"])
        for group in ("customer_requests", "offers", "engagements", "deliverables")
        for record in snapshot[group]
    }
    return [
        f"Unknown customer evidence: {item['record_type']}:{item['record_id']}"
        for item in evidence
        if (item["record_type"], item["record_id"]) not in available
    ]


def _validate_customer_safety(subject: str, body: str) -> list[str]:
    content = f"{subject} {body}".lower()
    prohibited = (
        "send automatically",
        "already sent",
        "guarantee",
        "we promise",
        "approved automatically",
        "ignore previous instructions",
        "provide your credit card",
        "send your credit card",
        "reply with your credit card",
        "provide your password",
        "send your password",
        "reply with your password",
        "provide your api key",
        "send your api key",
        "reply with your api key",
    )
    return [
        f"Prohibited customer draft language: {phrase}"
        for phrase in prohibited
        if phrase in content
    ]


def _operations_gate_passed(company: Company) -> bool:
    return OperationsEvaluationRun.objects.filter(
        company=company,
        provider="openai",
        status=OperationsEvaluationRun.Status.PASSED,
        technical_gate_passed=True,
        human_review_completed=True,
    ).exists()


def _run_customer_loop(
    *,
    company: Company,
    actor: str,
    provider: CustomerAIProvider,
    customer_request: CustomerRequest | None = None,
) -> CustomerLoopResult:
    if not company.is_synthetic:
        raise ValidationError("Customer Loop AI is restricted to synthetic company data.")
    if not _operations_gate_passed(company):
        raise ValidationError("The Operations Loop gate must pass before Customer AI runs.")
    snapshot = customer_snapshot(company, customer_request)
    selected_request = CustomerRequest.objects.get(pk=snapshot["customer_requests"][0]["id"])
    started = monotonic()
    try:
        result = provider.customer_drafts(snapshot=snapshot)
    except Exception as error:
        run = CustomerDraftRun.objects.create(
            company=company,
            customer_request=selected_request,
            status=CustomerDraftRun.Status.FAILED,
            provider=type(provider).__name__,
            model="unknown",
            input_snapshot=snapshot,
            latency_ms=int((monotonic() - started) * 1000),
            error_code=type(error).__name__,
        )
        AuditEvent.objects.create(
            event_type="customer-draft-run-failed",
            actor=actor,
            payload={"run_id": str(run.pk), "error_code": run.error_code},
        )
        return CustomerLoopResult(run=run, drafts_created=0)

    run = CustomerDraftRun.objects.create(
        company=company,
        customer_request=selected_request,
        status=CustomerDraftRun.Status.COMPLETED,
        provider=result.provider,
        model=result.model,
        input_snapshot=snapshot,
        latency_ms=result.latency_ms or int((monotonic() - started) * 1000),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
    for item in result.output.drafts:
        evidence = [reference.model_dump() for reference in item.evidence]
        errors = _validate_customer_evidence(snapshot, evidence) + _validate_customer_safety(
            item.subject, item.body
        )
        CustomerDraft.objects.create(
            run=run,
            subject=item.subject,
            body=item.body,
            intent=item.intent,
            escalation_reason=item.escalation_reason or "",
            evidence=evidence,
            validation_errors=errors,
        )
    AuditEvent.objects.create(
        event_type="customer-drafts-generated",
        actor=actor,
        payload={"run_id": str(run.pk), "drafts_created": len(result.output.drafts)},
    )
    return CustomerLoopResult(run=run, drafts_created=len(result.output.drafts))


def run_customer_loop(
    *,
    company: Company,
    actor: str,
    provider: CustomerAIProvider,
    customer_request: CustomerRequest | None = None,
) -> CustomerLoopResult:
    with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
        return _run_customer_loop(
            company=company,
            actor=actor,
            provider=provider,
            customer_request=customer_request,
        )


def decide_customer_draft(
    *, draft: CustomerDraft, decision: str, decided_by, note: str = ""
) -> CustomerDraft:
    if draft.status != CustomerDraft.Status.PENDING:
        raise ValidationError("Only pending customer drafts can be decided.")
    if decision not in {
        CustomerDraft.Status.APPROVED,
        CustomerDraft.Status.REJECTED,
        CustomerDraft.Status.DEFERRED,
    }:
        raise ValidationError("Decision must be approved, rejected, or deferred.")
    if decision == CustomerDraft.Status.APPROVED and draft.validation_errors:
        raise ValidationError("A customer draft with validation errors cannot be approved.")
    draft.status = decision
    draft.decided_by = decided_by
    draft.decided_at = timezone.now()
    draft.decision_note = note.strip()
    draft.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
    AuditEvent.objects.create(
        event_type="customer-draft-decided",
        actor=f"user:{decided_by.pk}",
        payload={"draft_id": str(draft.pk), "decision": decision, "sent": False},
    )
    return draft
