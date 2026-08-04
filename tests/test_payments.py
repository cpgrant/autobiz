from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from apps.operations.models import CustomerRequest, FinancialEntry, Offer
from apps.operations.payments import (
    create_stripe_checkout_session,
    handle_stripe_webhook,
    record_successful_payment,
)
from apps.operations.services import submit_synthetic_request


@pytest.fixture
def test_offer(db):
    call_command("load_customer_zero", verbosity=0)
    submitted = submit_synthetic_request(
        customer_name="Stripe Test Customer",
        email="stripe@example.invalid",
        request_text="Need automated lead follow up",
        desired_outcome="Quick onboarding",
    )
    return submitted.offer


@pytest.mark.django_db
def test_create_checkout_session_synthetic_fallback(test_offer):
    with patch.dict("os.environ", {}, clear=True):
        res = create_stripe_checkout_session(
            offer=test_offer,
            success_url="http://localhost:8000/success",
            cancel_url="http://localhost:8000/cancel",
        )
        assert res["is_synthetic"] is True
        assert "cs_test_" in res["session_id"]


@pytest.mark.django_db
@patch("stripe.checkout.Session.create")
def test_create_checkout_session_stripe(mock_session_create, test_offer):
    mock_session = MagicMock()
    mock_session.id = "cs_live_123"
    mock_session.url = "https://checkout.stripe.com/pay/cs_live_123"
    mock_session_create.return_value = mock_session

    with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_123"}):
        res = create_stripe_checkout_session(
            offer=test_offer,
            success_url="http://localhost:8000/success",
            cancel_url="http://localhost:8000/cancel",
        )
        assert res["is_synthetic"] is False
        assert res["session_id"] == "cs_live_123"


@pytest.mark.django_db
def test_record_successful_payment(test_offer):
    req = test_offer.customer_request
    entry = record_successful_payment(
        customer_request=req,
        amount_eur=Decimal("50.00"),
        reference="cs_live_123",
    )
    req.refresh_from_db()
    test_offer.refresh_from_db()

    assert req.status == CustomerRequest.Status.PAID
    assert test_offer.status == Offer.Status.ACCEPTED
    assert entry.amount_eur == Decimal("50.00")
    assert entry.entry_type == FinancialEntry.EntryType.REVENUE


@pytest.mark.django_db
def test_handle_stripe_webhook(test_offer):
    req = test_offer.customer_request
    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_session_123",
                "client_reference_id": str(req.id),
                "amount_total": 5000,
            }
        },
    }

    res = handle_stripe_webhook(payload=payload)
    assert res["status"] == "success"

    req.refresh_from_db()
    assert req.status == CustomerRequest.Status.PAID
