from dataclasses import dataclass
from decimal import Decimal
from time import monotonic

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .ai_providers import AIProvider
from .models import AuditEvent, Company, Suggestion, SuggestionRun, WorkItem


@dataclass(frozen=True)
class ManagementLoopResult:
    run: SuggestionRun
    suggestions_created: int


def management_snapshot(company: Company) -> dict:
    def json_value(value):
        return str(value) if isinstance(value, Decimal) else value

    def records(queryset, record_type: str, fields: tuple[str, ...]) -> list[dict]:
        return [
            {
                "record_type": record_type,
                "id": str(row.pk),
                **{field: json_value(getattr(row, field)) for field in fields},
            }
            for row in queryset
        ]

    return {
        "company": {"id": str(company.pk), "name": company.name, "mission": company.mission},
        "goals": records(
            company.goals.filter(status="active"),
            "goal",
            ("name", "current_value", "target_value", "unit"),
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
        "opportunities": records(
            company.opportunities.exclude(stage__in=["won", "lost"]),
            "opportunity",
            ("stage", "estimated_value_eur", "probability_percent"),
        ),
    }


def _validate_evidence(snapshot: dict, evidence: list[dict]) -> list[str]:
    available = {
        (record["record_type"], record["id"])
        for group in ("goals", "metrics", "risks", "work_items", "opportunities")
        for record in snapshot[group]
    }
    return [
        f"Unknown evidence reference: {item['record_type']}:{item['record_id']}"
        for item in evidence
        if (item["record_type"], item["record_id"]) not in available
    ]


def _validate_safety(title: str, rationale: str) -> list[str]:
    content = f"{title} {rationale}".lower()
    prohibited_phrases = (
        "approve automatically",
        "change permission",
        "execute external",
        "send email",
        "send payment",
    )
    return [
        f"Prohibited autonomous action language: {phrase}"
        for phrase in prohibited_phrases
        if phrase in content
    ]


def _run_management_loop(
    *, company: Company, actor: str, provider: AIProvider
) -> ManagementLoopResult:
    if not company.is_synthetic:
        raise ValidationError("Management Loop AI is restricted to synthetic company data.")
    snapshot = management_snapshot(company)
    started = monotonic()
    try:
        result = provider.management_suggestions(snapshot=snapshot)
    except Exception as error:
        run = SuggestionRun.objects.create(
            company=company,
            loop=SuggestionRun.Loop.MANAGEMENT,
            status=SuggestionRun.Status.FAILED,
            provider=type(provider).__name__,
            model="unknown",
            input_snapshot=snapshot,
            latency_ms=int((monotonic() - started) * 1000),
            error_code=type(error).__name__,
        )
        AuditEvent.objects.create(
            event_type="management-suggestion-run-failed",
            actor=actor,
            payload={"run_id": str(run.pk), "error_code": run.error_code},
        )
        return ManagementLoopResult(run=run, suggestions_created=0)

    run = SuggestionRun.objects.create(
        company=company,
        loop=SuggestionRun.Loop.MANAGEMENT,
        status=SuggestionRun.Status.COMPLETED,
        provider=result.provider,
        model=result.model,
        input_snapshot=snapshot,
        latency_ms=result.latency_ms or int((monotonic() - started) * 1000),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
    created = 0
    seen_titles: set[str] = set()
    for item in result.output.suggestions:
        evidence = [reference.model_dump() for reference in item.evidence]
        normalized_title = item.title.strip().casefold()
        errors = _validate_evidence(snapshot, evidence) + _validate_safety(
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
        created += 1
    AuditEvent.objects.create(
        event_type="management-suggestions-generated",
        actor=actor,
        payload={"run_id": str(run.pk), "suggestions_created": created},
    )
    return ManagementLoopResult(run=run, suggestions_created=created)


def run_management_loop(
    *, company: Company, actor: str, provider: AIProvider
) -> ManagementLoopResult:
    with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
        return _run_management_loop(company=company, actor=actor, provider=provider)


def _decide_suggestion(
    *, suggestion: Suggestion, decision: str, decided_by, note: str = ""
) -> Suggestion:
    if suggestion.status != Suggestion.Status.PENDING:
        raise ValidationError("Only pending suggestions can be decided.")
    if decision not in {
        Suggestion.Status.ACCEPTED,
        Suggestion.Status.REJECTED,
        Suggestion.Status.DEFERRED,
    }:
        raise ValidationError("Decision must be accepted, rejected, or deferred.")
    if decision == Suggestion.Status.ACCEPTED and suggestion.validation_errors:
        raise ValidationError("A suggestion with validation errors cannot be accepted.")
    suggestion.status = decision
    suggestion.decided_by = decided_by
    suggestion.decided_at = timezone.now()
    suggestion.decision_note = note
    if decision == Suggestion.Status.ACCEPTED:
        suggestion.work_item = WorkItem.objects.create(
            company=suggestion.run.company,
            key=f"ai-draft-{str(suggestion.pk)[:8]}-{slugify(suggestion.title)[:30]}",
            title=suggestion.title,
            function=suggestion.function,
            status=WorkItem.Status.PROPOSED,
            priority=3,
            requires_approval=False,
            is_synthetic=True,
        )
    suggestion.save(
        update_fields=[
            "status",
            "decided_by",
            "decided_at",
            "decision_note",
            "work_item",
            "updated_at",
        ]
    )
    AuditEvent.objects.create(
        event_type="management-suggestion-decided",
        actor=f"user:{decided_by.pk}",
        payload={
            "suggestion_id": str(suggestion.pk),
            "decision": decision,
            "work_item_id": str(suggestion.work_item_id) if suggestion.work_item_id else None,
        },
    )
    return suggestion


def decide_suggestion(
    *, suggestion: Suggestion, decision: str, decided_by, note: str = ""
) -> Suggestion:
    with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
        return _decide_suggestion(
            suggestion=suggestion,
            decision=decision,
            decided_by=decided_by,
            note=note,
        )
