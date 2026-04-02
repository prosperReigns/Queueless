"""Payment service logic."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentProvider, PaymentStatus
from app.models.user import User
from app.services.order_service import update_order_status
from app.tasks.notifications import queue_order_notification

logger = logging.getLogger(__name__)


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
        logger.error(
            "Payment initialization failed: missing Paystack secret key.",
            extra={"event": "payment_initialization_failed", "reason": "missing_secret_key"},
        )
        raise ValueError("Paystack secret key is not configured.")

    order = db.get(Order, order_id)
    if order is None:
        logger.warning(
            "Payment initialization failed: order not found.",
            extra={"event": "payment_initialization_failed", "order_id": order_id, "reason": "order_not_found"},
        )
        raise ValueError("Order not found.")
    if order.user_id != user.id:
        logger.warning(
            "Payment initialization failed: unauthorized user.",
            extra={
                "event": "payment_initialization_failed",
                "order_id": order_id,
                "user_id": str(user.id),
                "reason": "unauthorized_user",
            },
        )
        raise ValueError("Not enough permissions.")
    if order.status != OrderStatus.PENDING:
        logger.warning(
            "Payment initialization failed: order not pending.",
            extra={
                "event": "payment_initialization_failed",
                "order_id": order_id,
                "user_id": str(user.id),
                "order_status": order.status.value,
                "reason": "order_not_pending",
            },
        )
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
        logger.error(
            "Payment provider timeout during initialization.",
            extra={
                "event": "payment_initialization_failed",
                "order_id": order.id,
                "payment_reference": payment.reference,
                "reason": "provider_timeout",
            },
            exc_info=exc,
        )
        raise ValueError("Timed out while contacting payment provider.") from exc
    except httpx.HTTPError as exc:
        logger.error(
            "Payment provider network error during initialization.",
            extra={
                "event": "payment_initialization_failed",
                "order_id": order.id,
                "payment_reference": payment.reference,
                "reason": "provider_network_error",
            },
            exc_info=exc,
        )
        raise ValueError("Failed to contact payment provider due to network error.") from exc

    if response.status_code >= 400:
        error_body = response.text.strip()
        if len(error_body) > 300:
            error_body = f"{error_body[:300]}..."
        logger.warning(
            "Payment provider rejected initialization request.",
            extra={
                "event": "payment_initialization_failed",
                "order_id": order.id,
                "payment_reference": payment.reference,
                "provider_status_code": response.status_code,
                "reason": "provider_rejected_request",
            },
        )
        raise ValueError(
            f"Payment provider rejected initialization request (status={response.status_code}): "
            f"{error_body or 'no details'}"
        )

    data = response.json()
    if not data.get("status"):
        logger.warning(
            "Payment provider returned unsuccessful initialization payload.",
            extra={
                "event": "payment_initialization_failed",
                "order_id": order.id,
                "payment_reference": payment.reference,
                "reason": "provider_status_false",
            },
        )
        raise ValueError("Payment provider did not initialize transaction.")
    provider_data = data.get("data") or {}
    authorization_url = provider_data.get("authorization_url")
    access_code = provider_data.get("access_code")
    reference = provider_data.get("reference")
    if not authorization_url or not access_code or not reference:
        logger.warning(
            "Payment provider returned invalid initialization payload.",
            extra={
                "event": "payment_initialization_failed",
                "order_id": order.id,
                "payment_reference": payment.reference,
                "reason": "invalid_provider_payload",
            },
        )
        raise ValueError("Payment provider returned an invalid initialization response.")

    logger.info(
        "Payment initialized.",
        extra={
            "event": "payment_initialized",
            "order_id": order.id,
            "user_id": str(user.id),
            "payment_reference": payment.reference,
            "provider_reference": reference,
            "amount": str(payment.amount),
            "provider": payment.provider.value,
            "payment_status": payment.status.value,
        },
    )

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
        logger.warning(
            "Rejected payment webhook: invalid payload.",
            extra={"event": "payment_webhook_ignored", "reason": "invalid_payload"},
        )
        return (False, "invalid_payload")
    if event.get("event") != "charge.success":
        logger.info(
            "Ignored payment webhook event.",
            extra={
                "event": "payment_webhook_ignored",
                "reason": "unsupported_event",
                "webhook_event_type": event.get("event"),
            },
        )
        return (False, "unsupported_event")

    payload = event.get("data") or {}
    reference = payload.get("reference")
    if not reference:
        logger.warning(
            "Rejected payment webhook: missing payment reference.",
            extra={"event": "payment_webhook_ignored", "reason": "missing_reference"},
        )
        return (False, "missing_reference")

    payment = get_payment_by_reference(db, reference)
    if payment is None:
        logger.warning(
            "Ignored payment webhook: payment not found.",
            extra={
                "event": "payment_webhook_ignored",
                "reason": "payment_not_found",
                "payment_reference": reference,
            },
        )
        return (False, "payment_not_found")

    # Idempotent: already processed.
    if payment.status == PaymentStatus.SUCCESS:
        logger.info(
            "Ignored payment webhook: payment already processed.",
            extra={
                "event": "payment_webhook_idempotent",
                "reason": "already_processed",
                "payment_reference": reference,
                "payment_status": payment.status.value,
            },
        )
        return (True, "already_processed")
    if payment.status == PaymentStatus.FAILED:
        logger.info(
            "Ignored payment webhook: payment already failed.",
            extra={
                "event": "payment_webhook_idempotent",
                "reason": "payment_already_failed",
                "payment_reference": reference,
                "payment_status": payment.status.value,
            },
        )
        return (True, "payment_already_failed")

    payment.status = PaymentStatus.SUCCESS
    db.add(payment)

    order = db.get(Order, payment.order_id)
    if order is not None and order.status == OrderStatus.PENDING:
        db.commit()
        updated_order = update_order_status(
            db,
            order,
            OrderStatus.PAID,
            actor="payment_webhook",
        )
        queue_order_notification(updated_order.id, "order_paid")
        logger.info(
            "Order marked paid from payment webhook.",
            extra={
                "event": "order_payment_status_updated",
                "order_id": updated_order.id,
                "user_id": str(updated_order.user_id),
                "payment_reference": payment.reference,
                "payment_status": payment.status.value,
                "order_status": updated_order.status.value,
            },
        )
    else:
        db.commit()
    logger.info(
        "Payment webhook processed successfully.",
        extra={
            "event": "payment_webhook_processed",
            "payment_reference": payment.reference,
            "payment_status": payment.status.value,
            "order_id": payment.order_id,
        },
    )
    return (True, "processed")
