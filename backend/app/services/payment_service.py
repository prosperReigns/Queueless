"""Payment service logic."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentProvider, PaymentStatus
from app.models.user import User
from app.tasks.notifications import queue_order_notification


def get_payment_by_reference(db: Session, reference: str) -> Payment | None:
    """Return payment by provider reference if present."""
    stmt = select(Payment).where(Payment.reference == reference)
    return db.scalar(stmt)


def _get_or_create_payment_for_order(db: Session, order: Order) -> Payment:
    """Return existing payment for order reference or create pending payment."""
    payment = get_payment_by_reference(db, order.payment_reference)
    if payment is not None:
        return payment

    payment = Payment(
        order_id=order.id,
        reference=order.payment_reference,
        status=PaymentStatus.PENDING,
        amount=order.total_amount,
        provider=PaymentProvider.PAYSTACK,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def initialize_paystack_payment(
    db: Session,
    *,
    order_id: int,
    user: User,
    callback_url: str | None = None,
) -> dict[str, Any]:
    """Initialize Paystack transaction and persist pending payment."""
    settings = get_settings()
    if not settings.PAYSTACK_SECRET_KEY:
        raise ValueError("Paystack secret key is not configured.")

    order = db.get(Order, order_id)
    if order is None:
        raise ValueError("Order not found.")
    if order.user_id != user.id:
        raise ValueError("Not enough permissions.")
    if order.status != OrderStatus.PENDING:
        raise ValueError("Only pending orders can be initialized for payment.")

    payment = _get_or_create_payment_for_order(db, order)

    payload: dict[str, Any] = {
        "email": user.email,
        "amount": int(order.total_amount * 100),
        "reference": payment.reference,
    }
    if callback_url:
        payload["callback_url"] = callback_url

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            f"{settings.PAYSTACK_BASE_URL.rstrip('/')}/transaction/initialize",
            json=payload,
            headers=headers,
            timeout=15,
        )
    except httpx.TimeoutException as exc:
        raise ValueError("Timed out while contacting payment provider.") from exc
    except httpx.HTTPError as exc:
        raise ValueError("Failed to contact payment provider due to network error.") from exc

    if response.status_code >= 400:
        error_body = response.text.strip()
        if len(error_body) > 300:
            error_body = f"{error_body[:300]}..."
        raise ValueError(
            f"Payment provider rejected initialization request (status={response.status_code}): "
            f"{error_body or 'no details'}"
        )

    data = response.json()
    if not data.get("status"):
        raise ValueError("Payment provider did not initialize transaction.")
    provider_data = data.get("data") or {}
    authorization_url = provider_data.get("authorization_url")
    access_code = provider_data.get("access_code")
    reference = provider_data.get("reference")
    if not authorization_url or not access_code or not reference:
        raise ValueError("Payment provider returned an invalid initialization response.")

    return {
        "payment": payment,
        "authorization_url": authorization_url,
        "access_code": access_code,
        "reference": reference,
    }


def verify_paystack_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    """Verify Paystack webhook signature with HMAC SHA-512."""
    settings = get_settings()
    if not settings.PAYSTACK_SECRET_KEY or not signature:
        return False

    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_paystack_webhook_event(db: Session, raw_body: bytes) -> tuple[bool, str]:
    """Process webhook event idempotently and return (processed, reason)."""
    try:
        event = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return (False, "invalid_payload")
    if event.get("event") != "charge.success":
        return (False, "unsupported_event")

    payload = event.get("data") or {}
    reference = payload.get("reference")
    if not reference:
        return (False, "missing_reference")

    payment = get_payment_by_reference(db, reference)
    if payment is None:
        return (False, "payment_not_found")

    # Idempotent: already processed.
    if payment.status == PaymentStatus.SUCCESS:
        return (True, "already_processed")
    if payment.status == PaymentStatus.FAILED:
        return (True, "payment_already_failed")

    payment.status = PaymentStatus.SUCCESS
    db.add(payment)

    order = db.get(Order, payment.order_id)
    if order is not None and order.status == OrderStatus.PENDING:
        order.status = OrderStatus.PAID
        db.add(order)
        queue_order_notification(order.id, "order_paid")

    db.commit()
    return (True, "processed")
