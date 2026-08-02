from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from time import monotonic

from django.core.exceptions import ValidationError
from django.db import transaction

from .ai_providers import OperationsAIProvider
from .management_loop import _validate_safety
from .models import (
    AuditEvent,
    Company,
    ManagementEvaluationRun,
    OperatingCycle,
    Suggestion,
    SuggestionRun,
)


@dataclass(frozen=True)
class OperationsLoopResult:
    run: SuggestionRun
    suggestions_created: int


def operations_snapshot(company: Company) -> dict:
    def value(item):
        return str(item) if isinstance(item, (Decimal, date)) else item

    def records(queryset, record_type: str, fields: tuple[str, ...]) -> list[dict]:
        return [
            {
                "record_type": record_type,
                "id": str(row.pk),
                **{field: value(getattr(row, field)) for field in fields},
            }
            for row in queryset
        ]

    return {
        "company": {"id": str(company.pk), "name": company.name},
        "operating_cycles": records(
            company.operating_cycles.filter(status=OperatingCycle.Status.COMPLETED)[:5],
            "operating_cycle",
            ("operating_date", "status", "report"),
        ),
        "metrics": records(
            company.metrics.all(), "metric", ("name", "value", "target_value", "unit")
        ),
        "risks": records(
            company.risks.filter(status="open"), "risk", ("title", "severity", "mitigation")
        ),
        "work_items": records(
            company.work_items.exclude(status="done"),
            "work_item",
            ("title", "status", "priority", "function"),
        ),
    }


def _validate_operations_evidence(snapshot: dict, evidence: list[dict]) -> list[str]:
    available = {
        (record["record_type"], record["id"])
        for group in ("operating_cycles", "metrics", "risks", "work_items")
        for record in snapshot[group]
    }
    return [
        f"Unknown operations evidence: {item['record_type']}:{item['record_id']}"
        for item in evidence
        if (item["record_type"], item["record_id"]) not in available
    ]


def _management_gate_passed(company: Company) -> bool:
    return ManagementEvaluationRun.objects.filter(
        company=company,
        provider="openai",
        status=ManagementEvaluationRun.Status.PASSED,
        technical_gate_passed=True,
        human_review_completed=True,
    ).exists()


def _run_operations_loop(
    *, company: Company, actor: str, provider: OperationsAIProvider
) -> OperationsLoopResult:
    if not company.is_synthetic:
        raise ValidationError("Operations Loop AI is restricted to synthetic company data.")
    if not _management_gate_passed(company):
        raise ValidationError("The Management Loop gate must pass before Operations AI runs.")
    snapshot = operations_snapshot(company)
    if not snapshot["operating_cycles"]:
        raise ValidationError("At least one completed operating cycle is required.")
    latest_cycle = company.operating_cycles.filter(status=OperatingCycle.Status.COMPLETED).first()
    started = monotonic()
    try:
        result = provider.operations_suggestions(snapshot=snapshot)
    except Exception as error:
        run = SuggestionRun.objects.create(
            company=company,
            operating_cycle=latest_cycle,
            loop=SuggestionRun.Loop.OPERATIONS,
            status=SuggestionRun.Status.FAILED,
            provider=type(provider).__name__,
            model="unknown",
            input_snapshot=snapshot,
            latency_ms=int((monotonic() - started) * 1000),
            error_code=type(error).__name__,
        )
        AuditEvent.objects.create(
            event_type="operations-suggestion-run-failed",
            actor=actor,
            payload={"run_id": str(run.pk), "error_code": run.error_code},
        )
        return OperationsLoopResult(run=run, suggestions_created=0)

    run = SuggestionRun.objects.create(
        company=company,
        operating_cycle=latest_cycle,
        loop=SuggestionRun.Loop.OPERATIONS,
        status=SuggestionRun.Status.COMPLETED,
        provider=result.provider,
        model=result.model,
        input_snapshot=snapshot,
        latency_ms=result.latency_ms or int((monotonic() - started) * 1000),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
    seen_titles: set[str] = set()
    for item in result.output.suggestions:
        evidence = [reference.model_dump() for reference in item.evidence]
        normalized_title = item.title.strip().casefold()
        errors = _validate_operations_evidence(snapshot, evidence) + _validate_safety(
            item.title, item.rationale
        )
        if normalized_title in seen_titles:
            errors.append("Duplicate suggestion title within provider output.")
        seen_titles.add(normalized_title)
        Suggestion.objects.create(
            run=run,
            title=item.title,
            rationale=item.rationale,
            function=item.function,
            evidence=evidence,
            validation_errors=errors,
        )
    AuditEvent.objects.create(
        event_type="operations-suggestions-generated",
        actor=actor,
        payload={"run_id": str(run.pk), "suggestions_created": len(seen_titles)},
    )
    return OperationsLoopResult(run=run, suggestions_created=len(seen_titles))


def run_operations_loop(
    *, company: Company, actor: str, provider: OperationsAIProvider
) -> OperationsLoopResult:
    with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
        return _run_operations_loop(company=company, actor=actor, provider=provider)
