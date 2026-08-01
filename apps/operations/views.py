from django.db import connections
from django.db.models import Sum
from django.db.utils import OperationalError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import Company, FinancialEntry


def home(request):
    return HttpResponse(
        """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>Autobiz</title></head>
<body><main><h1>Autobiz</h1><p>Controlled business foundation is running.</p>
<ul><li><a href=\"/company/\">Customer Zero company status</a></li>
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


def company_status(request):
    company = get_object_or_404(Company, key="autobiz")
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
            "opportunities": company.opportunities.select_related("customer", "product"),
            "work_items": company.work_items.all()[:6],
            "risks": company.risks.filter(status="open"),
            "proposals": company.action_proposals.all(),
            "latest_cycle": company.operating_cycles.first(),
            "revenue": revenue,
            "costs": costs,
        },
    )
