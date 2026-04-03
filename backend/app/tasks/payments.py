"""Background tasks related to payments."""

from __future__ import annotations

import logging

import httpx
from celery.exceptions import CeleryError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.services.order_service import OrderStatusTransitionActor, update_order_status
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    bind=True,
    name="app.tasks.payments.verify_payment_backup_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def verify_payment_backup_task(self, payment_reference: str) -> str:  # noqa: ARG001
    """Verify payment status with provider as webhook fallback and reconcile order state."""
    payment = _get_payment_by_reference(payment_reference)
    if payment is None:
        return "payment_not_found"
    if payment.status == PaymentStatus.SUCCESS:
        return "already_success"
    if not settings.PAYSTACK_SECRET_KEY:
        return "missing_secret_key"

    provider_status = _fetch_paystack_transaction_status(payment_reference)
    if provider_status is None:
        raise RuntimeError("provider_status_unavailable")
    if provider_status != "success":
        return f"provider_status_{provider_status}"

    with SessionLocal() as db:
        fresh_payment = _get_payment_by_reference(payment_reference, db=db)
        if fresh_payment is None:
            return "payment_not_found"
        if fresh_payment.status == PaymentStatus.SUCCESS:
            return "already_success"

        fresh_payment.status = PaymentStatus.SUCCESS
        db.add(fresh_payment)

        order = db.get(Order, fresh_payment.order_id)
        if order is None:
            db.commit()
            return "payment_success_order_not_found"

        if order.status == OrderStatus.PENDING:
            update_order_status(
                db,
                order,
                OrderStatus.PAID,
                actor=OrderStatusTransitionActor.PAYMENT_WEBHOOK,
            )
            return "payment_and_order_reconciled"

        db.commit()
        return f"payment_reconciled_order_{order.status.value}"


def _get_payment_by_reference(reference: str, *, db: Session | None = None) -> Payment | None:
    """Read payment by reference, using provided session when available."""
    if db is not None:
        stmt = select(Payment).where(Payment.reference == reference)
        return db.scalar(stmt)
    with SessionLocal() as owned_db:
        stmt = select(Payment).where(Payment.reference == reference)
        return owned_db.scalar(stmt)


def _fetch_paystack_transaction_status(payment_reference: str) -> str | None:
    """Fetch transaction status from Paystack verify endpoint."""
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    url = f"{settings.PAYSTACK_BASE_URL.rstrip('/')}/transaction/verify/{payment_reference}"
    try:
        response = httpx.get(url, headers=headers, timeout=15)
    except httpx.HTTPError as exc:
        logger.warning(
            "Payment fallback verification request failed.",
            extra={"event": "payment_fallback_verification_failed", "payment_reference": payment_reference},
            exc_info=exc,
        )
        return None
    if response.status_code >= 400:
        logger.warning(
            "Payment fallback verification rejected by provider.",
            extra={
                "event": "payment_fallback_verification_rejected",
                "payment_reference": payment_reference,
                "provider_status_code": response.status_code,
            },
        )
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    if not payload.get("status"):
        return None
    data = payload.get("data") or {}
    status = data.get("status")
    return status.lower() if isinstance(status, str) else None


def schedule_payment_verification_fallback(payment_reference: str) -> None:
    """Schedule delayed payment verification fallback task."""
    try:
        verify_payment_backup_task.apply_async(
            args=[payment_reference],
            countdown=settings.PAYMENT_VERIFICATION_FALLBACK_DELAY_SECONDS,
        )
    except CeleryError as exc:
        logger.warning(
            "Failed to enqueue payment verification fallback task.",
            extra={"event": "payment_fallback_enqueue_failed", "payment_reference": payment_reference},
            exc_info=exc,
        )
