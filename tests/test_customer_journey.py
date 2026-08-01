import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.operations.models import (
    AuditEvent,
    CustomerRequest,
    Deliverable,
    Engagement,
    FinancialEntry,
    SyntheticPayment,
    WorkItem,
)
from apps.operations.services import simulate_payment_and_delivery


@pytest.fixture
def synthetic_scenario(db):
    call_command("load_customer_zero", verbosity=0)


def submit_request(client):
    return client.post(
        reverse("customer-request"),
        {
            "customer_name": "Customer Zero — Test Founder",
            "email": "founder@example.invalid",
            "service": "establish",
            "request_text": "Create a controlled operating plan for my consultancy.",
            "desired_outcome": "A measurable weekly operating rhythm.",
        },
    )


@pytest.mark.django_db
def test_customer_can_complete_synthetic_request_to_deliverable(client, synthetic_scenario):
    response = submit_request(client)
    customer_request = CustomerRequest.objects.get(customer__name="Customer Zero — Test Founder")
    assert response.status_code == 302
    assert response.url == reverse("customer-offer", args=[customer_request.pk])
    assert customer_request.is_synthetic
    assert customer_request.offer.price_eur == 1200

    response = client.post(reverse("customer-accept-offer", args=[customer_request.pk]))
    assert response.url == reverse("customer-payment", args=[customer_request.pk])

    response = client.post(reverse("customer-simulate-payment", args=[customer_request.pk]))
    assert response.url == reverse("customer-engagement", args=[customer_request.pk])

    customer_request.refresh_from_db()
    assert customer_request.status == CustomerRequest.Status.DELIVERED
    assert customer_request.engagement is not None
    assert SyntheticPayment.objects.get(offer=customer_request.offer).status == "paid"
    assert WorkItem.objects.filter(engagement=customer_request.engagement).count() == 4
    assert Deliverable.objects.get(customer_request=customer_request).is_synthetic
    assert FinancialEntry.objects.filter(key__startswith="portal-payment-").count() == 1
    assert AuditEvent.objects.filter(event_type="synthetic-payment-recorded").count() == 1


@pytest.mark.django_db
def test_simulated_payment_and_delivery_are_idempotent(client, synthetic_scenario):
    submit_request(client)
    customer_request = CustomerRequest.objects.latest("created_at")
    client.post(reverse("customer-accept-offer", args=[customer_request.pk]))

    simulate_payment_and_delivery(customer_request=customer_request)
    simulate_payment_and_delivery(customer_request=customer_request)

    assert SyntheticPayment.objects.filter(offer=customer_request.offer).count() == 1
    assert Engagement.objects.filter(customer_request=customer_request).count() == 1
    assert FinancialEntry.objects.filter(key__startswith="portal-payment-").count() == 1
    assert Deliverable.objects.filter(customer_request=customer_request).count() == 1


@pytest.mark.django_db
def test_customer_can_accept_deliverable(client, synthetic_scenario):
    submit_request(client)
    customer_request = CustomerRequest.objects.latest("created_at")
    client.post(reverse("customer-accept-offer", args=[customer_request.pk]))
    client.post(reverse("customer-simulate-payment", args=[customer_request.pk]))

    response = client.post(
        reverse("customer-deliverable", args=[customer_request.pk]),
        {"decision": "accept", "revision_note": ""},
    )

    assert response.status_code == 302
    customer_request.refresh_from_db()
    assert customer_request.status == CustomerRequest.Status.COMPLETED
    assert customer_request.deliverable.status == Deliverable.Status.ACCEPTED

    dashboard = client.get(reverse("company-status"))
    content = dashboard.content.decode()
    assert "Recent synthetic customer journeys" in content
    assert "Customer Zero — Test Founder" in content
    assert "Completed" in content


@pytest.mark.django_db
def test_revision_requires_a_note(client, synthetic_scenario):
    submit_request(client)
    customer_request = CustomerRequest.objects.latest("created_at")
    client.post(reverse("customer-accept-offer", args=[customer_request.pk]))
    client.post(reverse("customer-simulate-payment", args=[customer_request.pk]))

    response = client.post(
        reverse("customer-deliverable", args=[customer_request.pk]),
        {"decision": "revise", "revision_note": ""},
    )

    assert response.status_code == 200
    assert "Describe the requested revision" in response.content.decode()
    customer_request.refresh_from_db()
    assert customer_request.status == CustomerRequest.Status.DELIVERED


@pytest.mark.django_db
def test_customer_input_is_escaped_in_deliverable(client, synthetic_scenario):
    response = client.post(
        reverse("customer-request"),
        {
            "customer_name": "<script>alert('name')</script>",
            "email": "test@example.invalid",
            "service": "establish",
            "request_text": "<script>alert('request')</script>",
            "desired_outcome": "Safe output",
        },
    )
    assert response.status_code == 302
    customer_request = CustomerRequest.objects.latest("created_at")
    client.post(reverse("customer-accept-offer", args=[customer_request.pk]))
    client.post(reverse("customer-simulate-payment", args=[customer_request.pk]))

    response = client.get(reverse("customer-deliverable", args=[customer_request.pk]))

    assert "<script>" not in response.content.decode()
    assert "&lt;script&gt;" in response.content.decode()
