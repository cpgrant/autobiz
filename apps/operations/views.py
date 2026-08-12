import json
import os

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.db import connections
from django.db.models import Sum
from django.db.utils import OperationalError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .ai_providers import get_ai_provider

from .customer_evaluation import decide_customer_evaluation, run_customer_evaluation
from .customer_loop import decide_customer_draft, run_customer_loop
from .cycle_services import run_daily_cycle
from .forms import DeliverableReviewForm, SyntheticCustomerRequestForm
from .live_management_evaluation import (
    decide_live_management_evaluation,
    run_live_management_evaluation,
)
from .management_evaluation import run_management_evaluation
from .management_loop import decide_suggestion, run_management_loop
from .models import (
    Approval,
    AuditEvent,
    Company,
    CustomerDraft,
    CustomerEvaluationRun,
    CustomerRequest,
    Deliverable,
    FinancialEntry,
    ManagementEvaluationRun,
    Offer,
    OperationsEvaluationRun,
    Opportunity,
    Suggestion,
    SuggestionRun,
    SyntheticPayment,
    WorkItem,
)
from .operations_evaluation import (
    decide_operations_evaluation,
    run_operations_evaluation,
)
from .operations_loop import run_operations_loop
from .payments import create_stripe_checkout_session, handle_stripe_webhook
from .services import (
    accept_synthetic_offer,
    decide_approval,
    produce_revised_deliverable,
    refresh_company_state,
    review_deliverable,
    simulate_payment_and_delivery,
    submit_synthetic_request,
)


def home(request):
    return HttpResponse(
        """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>Autobiz</title></head>
<body><main><h1>Autobiz</h1><p>Controlled business foundation is running.</p>
<ul><li><a href=\"/customer/request/\">Start synthetic customer journey</a></li>
<li><a href=\"/company/\">Customer Zero company status</a></li>
<li><a href=\"/operator/\">Operator console</a></li>
<li><a href=\"/health/\">Health</a></li><li><a href=\"/ready/\">Readiness</a></li>
<li><a href=\"/admin/\">Django admin</a></li></ul></main></body></html>"""
    )


def health(request):
    return JsonResponse({"status": "ok", "service": "autobiz"})


def readiness(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        return JsonResponse(
            {"status": "not_ready", "service": "autobiz", "database": "unavailable"},
            status=503,
        )
    return JsonResponse({"status": "ready", "service": "autobiz", "database": "ok"})


@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not os.getenv("STRIPE_WEBHOOK_SECRET") or not request.headers.get(
        "Stripe-Signature"
    ):
        return JsonResponse({"error": "Stripe webhook verification is not configured"}, status=400)
    try:
        result = handle_stripe_webhook(
            payload=request.body,
            sig_header=request.headers.get("Stripe-Signature"),
        )
    except (ValueError, json.JSONDecodeError) as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse(result)


def company_status(request):
    company = get_object_or_404(Company, key="autobiz")
    open_opportunities = company.opportunities.exclude(
        stage__in=[Opportunity.Stage.WON, Opportunity.Stage.LOST]
    ).select_related("customer", "product")
    revenue = (
        company.financial_entries.filter(entry_type=FinancialEntry.EntryType.REVENUE).aggregate(
            total=Sum("amount_eur")
        )["total"]
        or 0
    )
    costs = (
        company.financial_entries.filter(entry_type=FinancialEntry.EntryType.COST).aggregate(
            total=Sum("amount_eur")
        )["total"]
        or 0
    )
    return render(
        request,
        "operations/company_status.html",
        {
            "company": company,
            "goals": company.goals.all(),
            "metrics": company.metrics.all(),
            "opportunities": open_opportunities,
            "recent_requests": company.customer_requests.select_related("customer", "product")[:5],
            "work_items": company.work_items.all()[:6],
            "risks": company.risks.filter(status="open"),
            "proposals": company.action_proposals.all(),
            "latest_cycle": company.operating_cycles.first(),
            "revenue": revenue,
            "costs": costs,
        },
    )


def format_evidence(evidence):
    labels = {
        "customer_request": "Customer Request",
        "operating_cycle": "Operating Cycle",
        "work_item": "Work Item",
        "risk": "Risk",
        "metric": "Metric",
        "goal": "Goal",
        "offer": "Offer",
        "deliverable": "Deliverable",
        "engagement": "Engagement",
    }

    formatted = []

    for item in evidence or []:
        record_type = item.get("record_type", "")
        formatted.append(
            {
                "label": labels.get(
                    record_type,
                    record_type.replace("_", " ").title(),
                ),
                "id": item.get("record_id"),
            }
        )

    return formatted



@staff_member_required
def operator_dashboard(request):
    company = get_object_or_404(Company, key="autobiz")
    pending_approvals = Approval.objects.filter(
        status=Approval.Status.PENDING,
        workflow_run__engagement__customer__company=company,
    ).select_related("workflow_run", "workflow_run__engagement")
    latest_management_run = (
        SuggestionRun.objects
        .filter(
            company=company,
            loop="management",
            status=SuggestionRun.Status.COMPLETED,
        )
        .order_by("-created_at")
        .first()
    )

    management_suggestions = list(
        Suggestion.objects.filter(
            run=latest_management_run
        ).select_related("run", "work_item")[:10]
    )



    operations_suggestions = list(
        Suggestion.objects.filter(
            run__company=company,
            run__loop="operations"
        ).select_related("run", "work_item")[:10]
    )

    customer_drafts = list(
        CustomerDraft.objects.filter(
            run__company=company
        ).select_related(
            "run",
            "run__customer_request"
        )[:10]
    )


    return render(
        request,
        "operations/operator_dashboard.html",
        {
            "company": company,
            "metrics": company.metrics.all(),
            "work_items": company.work_items.exclude(status=WorkItem.Status.DONE)[:10],
            "pending_approvals": pending_approvals,
            "cycles": company.operating_cycles.all()[:10],
            "weekly_reports": company.weekly_reports.all()[:8],
            "audit_events": AuditEvent.objects.order_by("-created_at")[:20],
            "latest_management_run": latest_management_run,

            "management_suggestions": management_suggestions,

            "operations_suggestions": operations_suggestions,

            "management_evaluations": company.management_evaluation_runs.prefetch_related("cases")[
                :5
            ],
            "operations_evaluations": company.operations_evaluation_runs.prefetch_related("cases")[
                :5
            ],

            "customer_drafts": customer_drafts,

            "customer_evaluations": company.customer_evaluation_runs.prefetch_related("cases")[:5],
        },
    )


@staff_member_required
@require_POST
def operator_refresh(request):
    company = get_object_or_404(Company, key="autobiz")
    result = refresh_company_state(company=company, actor=f"user:{request.user.pk}")
    messages.success(
        request,
        f"Refreshed {result.metrics_updated} metrics and prioritized "
        f"{result.work_items_prioritized} work items.",
    )
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_run_cycle(request):
    company = get_object_or_404(Company, key="autobiz")
    result = run_daily_cycle(company=company, actor=f"user:{request.user.pk}")
    messages.success(
        request,
        f"Completed synthetic day {result.cycle.operating_date}: "
        f"{result.internal_actions_simulated} bounded action simulated and "
        f"{result.approvals_requested} approval request created.",
    )
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_run_management_loop(request):
    company = get_object_or_404(Company, key="autobiz")
    result = run_management_loop(
        company=company,
        actor=f"user:{request.user.pk}",
        provider=get_ai_provider(),
    )
    if result.run.status == result.run.Status.FAILED:
        messages.error(request, "Management suggestion run failed safely.")
    else:
        messages.success(request, f"Created {result.suggestions_created} management suggestion.")
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_run_management_evaluation(request):
    company = get_object_or_404(Company, key="autobiz")
    result = run_management_evaluation(company=company, actor=f"user:{request.user.pk}")
    message = (
        f"Management evaluation {result.status}: "
        f"{result.cases_passed}/{result.cases_total} cases passed."
    )
    if result.status == result.Status.PASSED:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_run_live_management_evaluation(request):
    company = get_object_or_404(Company, key="autobiz", is_synthetic=True)
    result = run_live_management_evaluation(
        company=company,
        actor=f"user:{request.user.pk}",
    )
    message = (
        f"Live Management evaluation {result.status}: "
        f"{result.cases_passed}/{result.cases_total} cases passed."
    )
    if result.status == result.Status.NEEDS_REVIEW:
        messages.success(request, f"{message} Human usefulness review is required.")
    else:
        messages.error(request, message)
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_decide_live_management_evaluation(request, evaluation_id, decision):
    company = get_object_or_404(Company, key="autobiz")
    evaluation = get_object_or_404(
        company.management_evaluation_runs,
        pk=evaluation_id,
        provider="openai",
        status=ManagementEvaluationRun.Status.NEEDS_REVIEW,
    )
    try:
        decide_live_management_evaluation(
            evaluation=evaluation,
            decision=decision,
            decided_by=request.user,
            note=request.POST.get("note", ""),
        )
    except ValidationError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Live Management evaluation marked {decision}.")
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_decide_suggestion(request, suggestion_id, decision):
    company = get_object_or_404(Company, key="autobiz")
    suggestion = get_object_or_404(
        Suggestion,
        pk=suggestion_id,
        run__company=company,
        status=Suggestion.Status.PENDING,
    )
    try:
        decide_suggestion(
            suggestion=suggestion,
            decision=decision,
            decided_by=request.user,
            note=request.POST.get("note", ""),
        )
    except ValidationError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Suggestion {decision}.")
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_run_operations_loop(request):
    company = get_object_or_404(Company, key="autobiz")
    try:
        result = run_operations_loop(
            company=company,
            actor=f"user:{request.user.pk}",
            provider=get_ai_provider(),
        )
    except ValidationError as error:
        messages.error(request, str(error))
    else:
        if result.run.status == result.run.Status.FAILED:
            messages.error(request, "Operations suggestion run failed safely.")
        else:
            messages.success(
                request, f"Created {result.suggestions_created} Operations suggestion."
            )
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_run_operations_evaluation(request, mode):
    company = get_object_or_404(Company, key="autobiz", is_synthetic=True)
    live = mode == "live"
    if mode not in {"offline", "live"}:
        messages.error(request, "Unknown Operations evaluation mode.")
        return redirect("operator-dashboard")
    try:
        result = run_operations_evaluation(
            company=company,
            actor=f"user:{request.user.pk}",
            live=live,
        )
    except ValidationError as error:
        messages.error(request, str(error))
    else:
        message = (
            f"Operations evaluation {result.status}: "
            f"{result.cases_passed}/{result.cases_total} cases passed."
        )
        if result.status in {result.Status.PASSED, result.Status.NEEDS_REVIEW}:
            messages.success(request, message)
        else:
            messages.error(request, message)
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_decide_operations_evaluation(request, evaluation_id, decision):
    company = get_object_or_404(Company, key="autobiz")
    evaluation = get_object_or_404(
        company.operations_evaluation_runs,
        pk=evaluation_id,
        provider="openai",
        status=OperationsEvaluationRun.Status.NEEDS_REVIEW,
    )
    try:
        decide_operations_evaluation(
            evaluation=evaluation,
            decision=decision,
            decided_by=request.user,
            note=request.POST.get("note", ""),
        )
    except ValidationError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Operations evaluation marked {decision}.")
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_run_customer_loop(request):
    company = get_object_or_404(Company, key="autobiz", is_synthetic=True)
    try:
        result = run_customer_loop(
            company=company, actor=f"user:{request.user.pk}", provider=get_ai_provider()
        )
    except ValidationError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Created {result.drafts_created} customer draft for review.")
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_run_customer_evaluation(request, mode):
    company = get_object_or_404(Company, key="autobiz", is_synthetic=True)
    if mode not in {"offline", "live"}:
        messages.error(request, "Unknown Customer evaluation mode.")
        return redirect("operator-dashboard")
    try:
        result = run_customer_evaluation(
            company=company, actor=f"user:{request.user.pk}", live=mode == "live"
        )
    except ValidationError as error:
        messages.error(request, str(error))
    else:
        message = (
            f"Customer evaluation {result.status}: "
            f"{result.cases_passed}/{result.cases_total} cases passed."
        )
        if result.status in {result.Status.PASSED, result.Status.NEEDS_REVIEW}:
            messages.success(request, message)
        else:
            messages.error(request, message)
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_decide_customer_draft(request, draft_id, decision):
    company = get_object_or_404(Company, key="autobiz")
    draft = get_object_or_404(
        CustomerDraft,
        pk=draft_id,
        run__company=company,
        status=CustomerDraft.Status.PENDING,
    )
    try:
        decide_customer_draft(
            draft=draft,
            decision=decision,
            decided_by=request.user,
            note=request.POST.get("note", ""),
        )
    except ValidationError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Customer draft marked {decision}; nothing was sent.")
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_decide_customer_evaluation(request, evaluation_id, decision):
    company = get_object_or_404(Company, key="autobiz")
    evaluation = get_object_or_404(
        CustomerEvaluationRun,
        pk=evaluation_id,
        company=company,
        provider="openai",
        status=CustomerEvaluationRun.Status.NEEDS_REVIEW,
    )
    try:
        decide_customer_evaluation(
            evaluation=evaluation,
            decision=decision,
            decided_by=request.user,
            note=request.POST.get("note", ""),
        )
    except ValidationError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Customer evaluation marked {decision}.")
    return redirect("operator-dashboard")


@staff_member_required
@require_POST
def operator_decide_approval(request, approval_id, decision):
    company = get_object_or_404(Company, key="autobiz")
    approval = get_object_or_404(
        Approval,
        pk=approval_id,
        status=Approval.Status.PENDING,
        workflow_run__engagement__customer__company=company,
    )
    try:
        decide_approval(
            approval=approval,
            decision=decision,
            decided_by=request.user,
            note=request.POST.get("note", ""),
        )
    except ValidationError as error:
        messages.error(request, str(error))
    else:
        refresh_company_state(company=company, actor=f"user:{request.user.pk}")
        messages.success(request, f"Approval {decision}. External execution remains disabled.")
    return redirect("operator-dashboard")


def customer_request(request):
    form = SyntheticCustomerRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = submit_synthetic_request(
            customer_name=form.cleaned_data["customer_name"],
            email=form.cleaned_data["email"],
            request_text=form.cleaned_data["request_text"],
            desired_outcome=form.cleaned_data["desired_outcome"],
        )
        return redirect("customer-offer", request_id=result.customer_request.pk)
    return render(request, "operations/customer_request.html", {"form": form})


def _synthetic_request(request_id):
    return get_object_or_404(
        CustomerRequest.objects.select_related("company", "customer", "product", "engagement"),
        pk=request_id,
        is_synthetic=True,
        company__key="autobiz",
    )


def customer_offer(request, request_id):
    customer_request_record = _synthetic_request(request_id)
    return render(
        request,
        "operations/customer_offer.html",
        {"customer_request": customer_request_record, "offer": customer_request_record.offer},
    )


@require_POST
def customer_accept_offer(request, request_id):
    customer_request_record = _synthetic_request(request_id)
    accept_synthetic_offer(customer_request=customer_request_record)
    return redirect("customer-payment", request_id=request_id)


def customer_payment(request, request_id):
    customer_request_record = _synthetic_request(request_id)
    if customer_request_record.offer.status != Offer.Status.ACCEPTED:
        return redirect("customer-offer", request_id=request_id)
    if SyntheticPayment.objects.filter(offer=customer_request_record.offer).exists():
        return redirect("customer-engagement", request_id=request_id)

    success_url = request.build_absolute_uri(
        f"/customer/{request_id}/engagement/"
    )
    cancel_url = request.build_absolute_uri(
        f"/customer/{request_id}/payment/"
    )
    checkout_session = create_stripe_checkout_session(
        offer=customer_request_record.offer,
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return render(
        request,
        "operations/customer_payment.html",
        {
            "customer_request": customer_request_record,
            "offer": customer_request_record.offer,
            "checkout_session": checkout_session,
        },
    )


@require_POST
def customer_simulate_payment(request, request_id):
    customer_request_record = _synthetic_request(request_id)
    simulate_payment_and_delivery(customer_request=customer_request_record)
    return redirect("customer-engagement", request_id=request_id)


def customer_engagement(request, request_id):
    customer_request_record = _synthetic_request(request_id)
    if customer_request_record.engagement_id is None:
        return redirect("customer-payment", request_id=request_id)
    return render(
        request,
        "operations/customer_engagement.html",
        {
            "customer_request": customer_request_record,
            "engagement": customer_request_record.engagement,
            "work_items": customer_request_record.engagement.work_items.all(),
            "deliverable": customer_request_record.deliverables.get(is_current=True),
        },
    )


def customer_deliverable(request, request_id):
    customer_request_record = _synthetic_request(request_id)
    artifact = get_object_or_404(
        Deliverable, customer_request=customer_request_record, is_current=True
    )
    form = DeliverableReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review_deliverable(
            customer_request=customer_request_record,
            decision=form.cleaned_data["decision"],
            revision_note=form.cleaned_data["revision_note"],
        )
        return redirect("customer-deliverable", request_id=request_id)
    return render(
        request,
        "operations/customer_deliverable.html",
        {
            "customer_request": customer_request_record,
            "deliverable": artifact,
            "deliverable_versions": customer_request_record.deliverables.all(),
            "form": form,
        },
    )


@require_POST
def customer_simulate_revision(request, request_id):
    customer_request_record = _synthetic_request(request_id)
    produce_revised_deliverable(customer_request=customer_request_record)
    return redirect("customer-deliverable", request_id=request_id)
