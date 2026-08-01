from django.contrib import admin
from django.urls import path

from apps.operations.views import (
    company_status,
    customer_accept_offer,
    customer_deliverable,
    customer_engagement,
    customer_offer,
    customer_payment,
    customer_request,
    customer_simulate_payment,
    customer_simulate_revision,
    health,
    home,
    operator_dashboard,
    operator_decide_approval,
    operator_refresh,
    readiness,
)

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("company/", company_status, name="company-status"),
    path("operator/", operator_dashboard, name="operator-dashboard"),
    path("operator/refresh/", operator_refresh, name="operator-refresh"),
    path(
        "operator/approvals/<uuid:approval_id>/decide/<slug:decision>/",
        operator_decide_approval,
        name="operator-decide-approval",
    ),
    path("customer/request/", customer_request, name="customer-request"),
    path("customer/<uuid:request_id>/offer/", customer_offer, name="customer-offer"),
    path(
        "customer/<uuid:request_id>/offer/accept/",
        customer_accept_offer,
        name="customer-accept-offer",
    ),
    path("customer/<uuid:request_id>/payment/", customer_payment, name="customer-payment"),
    path(
        "customer/<uuid:request_id>/payment/simulate/",
        customer_simulate_payment,
        name="customer-simulate-payment",
    ),
    path(
        "customer/<uuid:request_id>/engagement/",
        customer_engagement,
        name="customer-engagement",
    ),
    path(
        "customer/<uuid:request_id>/deliverable/",
        customer_deliverable,
        name="customer-deliverable",
    ),
    path(
        "customer/<uuid:request_id>/deliverable/revise/simulate/",
        customer_simulate_revision,
        name="customer-simulate-revision",
    ),
    path("health/", health, name="health"),
    path("ready/", readiness, name="readiness"),
]
