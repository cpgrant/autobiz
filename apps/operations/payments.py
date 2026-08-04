import json
import logging
import os
from decimal import Decimal
from typing import Any

import stripe
from django.db import transaction
from django.utils import timezone

from .models import CustomerRequest, FinancialEntry, Offer

logger = logging.getLogger(__name__)


def get_stripe_client() -> Any | None:
    """Retrieve Stripe API key from environment."""
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if not api_key:
        return None
    stripe.api_key = api_key
    return stripe


def create_stripe_checkout_session(
    *,
    offer: Offer,
    success_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    """Create a Stripe Checkout Session for an accepted or proposed Offer.

    If STRIPE_SECRET_KEY is not configured, returns a deterministic test session response.
    """
    client = get_stripe_client()
    price_cents = int(Decimal(str(offer.price_eur)) * 100)

    if not client:
        logger.warning("STRIPE_SECRET_KEY missing; returning synthetic checkout session.")
        session_id = f"cs_test_{offer.id.hex[:16]}"
        checkout_url = f"{success_url}?session_id={session_id}&test=true"
        return {
            "session_id": session_id,
            "url": checkout_url,
            "is_synthetic": True,
        }

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {
                            "name": str(offer.title),
                            "description": str(offer.scope)[:250],
                        },
                        "unit_amount": price_cents,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url,
            client_reference_id=str(offer.customer_request.id),
            metadata={
                "offer_id": str(offer.id),
                "customer_request_id": str(offer.customer_request.id),
                "company_key": offer.customer_request.company.key,
            },
        )
        return {
            "session_id": session.id,
            "url": session.url,
            "is_synthetic": False,
        }
    except Exception as exc:
        logger.error("Failed to create Stripe Checkout Session: %s", exc)
        raise RuntimeError(f"Stripe Checkout Session creation failed: {exc}") from exc


def record_successful_payment(
    *,
    customer_request: CustomerRequest,
    amount_eur: Decimal,
    reference: str,
) -> FinancialEntry:
    """Record payment received for a customer request, update offer status, and log cash revenue."""
    with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
        offer = getattr(customer_request, "offer", None)
        if offer and offer.status != Offer.Status.ACCEPTED:
            offer.status = Offer.Status.ACCEPTED
            offer.accepted_at = timezone.now()
            offer.save(update_fields=["status", "accepted_at", "updated_at"])

        customer_request.status = CustomerRequest.Status.PAID
        customer_request.save(update_fields=["status", "updated_at"])

        key = f"rev-{customer_request.id.hex[:12]}-{int(timezone.now().timestamp())}"
        ledger_entry = FinancialEntry.objects.create(
            company=customer_request.company,
            key=key,
            entry_type=FinancialEntry.EntryType.REVENUE,
            amount_eur=amount_eur,
            description=f"Payment for Request {customer_request.id} ({reference})"[:240],
            occurred_on=timezone.now().date(),
            is_synthetic=customer_request.is_synthetic,
        )
        return ledger_entry


def handle_stripe_webhook(
    *, payload: bytes | str | dict[str, Any], sig_header: str | None = None
) -> dict[str, Any]:
    """Process incoming Stripe webhook events."""
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if webhook_secret and sig_header:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload if isinstance(payload, (bytes, str)) else json.dumps(payload),
                sig_header=sig_header,
                secret=webhook_secret,
            )
        except Exception as exc:
            logger.error("Invalid Stripe webhook signature: %s", exc)
            raise ValueError(f"Webhook signature verification failed: {exc}") from exc
    elif isinstance(payload, dict):
        event = payload
    else:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        event = json.loads(payload)

    event_type = event.get("type", "")
    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        request_id = session.get("client_reference_id") or session.get("metadata", {}).get(
            "customer_request_id"
        )
        amount_cents = session.get("amount_total", 0)
        amount_eur = Decimal(amount_cents) / Decimal(100)

        if request_id:
            try:
                customer_request = CustomerRequest.objects.get(id=request_id)
                record_successful_payment(
                    customer_request=customer_request,
                    amount_eur=amount_eur,
                    reference=str(session.get("id", "stripe_event")),
                )
                return {"status": "success", "processed_request": request_id}
            except CustomerRequest.DoesNotExist:
                logger.error("CustomerRequest ID %s not found for payment webhook", request_id)

    return {"status": "ignored", "event_type": event_type}
