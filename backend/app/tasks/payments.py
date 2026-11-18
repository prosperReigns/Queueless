"""Background payment verification and reconciliation tasks."""
from __future__ import annotations
import logging
from celery.exceptions import CeleryError
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

@celery_app.task(
    bind=True,
    name="app.tasks.payments.verify_payment_fallback_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def verify_payment_fallback_task(self, payment_reference: str) -> str:  # noqa: ARG001
    """Verify with Paystack and reconcile payment/order from provider truth."""
    if not settings.PAYSTACK_SECRET_KEY:
        return "missing_secret_key"
    from app.services.payment_service import verify_payment_and_reconcile
    with SessionLocal() as db:
        try:
            payment, provider_status = verify_payment_and_reconcile(db, payment_reference, source="fallback_verification")
        except ValueError as exc:
            # A transient provider/network failure should be retried by Celery.
            raise RuntimeError(str(exc)) from exc
        if provider_status == "success":
            return "payment_and_order_reconciled"
        if provider_status in {"pending", "ongoing", "processing", "queued", "unknown"}:
            raise RuntimeError(f"Paystack transaction is still {provider_status}; retry reconciliation.")
        return f"provider_status_{provider_status}"


def schedule_payment_verification_fallback(payment_reference: str) -> None:
    """Schedule a delayed server-side verification if webhook/callback is missed."""
    try:
        verify_payment_fallback_task.apply_async(
            args=[payment_reference],
            countdown=settings.PAYMENT_VERIFICATION_FALLBACK_DELAY_SECONDS,
        )
    except CeleryError:
        logger.exception(
            "Could not enqueue payment verification fallback",
            extra={"event": "payment_fallback_enqueue_failed", "payment_reference": payment_reference},
        )
