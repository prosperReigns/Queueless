"""Paystack payment initialization, verification, webhook processing and refunds."""
from __future__ import annotations
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.order import Order, OrderStatus
from app.models.payment import (
    Payment, PaymentEvent, PaymentProvider, PaymentRefund,
    PaymentStatus, PaymentStatusHistory,
)
from app.models.user import User
from app.services.order_service import OrderStatusTransitionActor, update_order_status
from app.tasks.payments import schedule_payment_verification_fallback

logger = logging.getLogger(__name__)
PAYSTACK_TIMEOUT_SECONDS = 15
CURRENCY = "NGN"


def get_payment_by_reference(db: Session, reference: str) -> Optional[Payment]:
    return db.scalar(select(Payment).where(Payment.reference == reference))


def _get_or_create_payment_for_order(db: Session, order: Order) -> Payment:
    payment = get_payment_by_reference(db, order.payment_reference)
    if payment is not None:
        return payment
    payment = Payment(
        order_id=order.id, reference=order.payment_reference,
        status=PaymentStatus.PENDING, amount=order.total_amount,
        currency=CURRENCY, provider=PaymentProvider.PAYSTACK,
    )
    db.add(payment)
    db.flush()
    return payment


def _headers() -> Dict[str, str]:
    key = get_settings().PAYSTACK_SECRET_KEY
    if not key:
        raise ValueError("Paystack secret key is not configured.")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _provider_request(method: str, path: str, *, payload: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    settings = get_settings()
    url = f"{settings.PAYSTACK_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    try:
        response = httpx.request(method, url, headers=_headers(), json=payload, params=params, timeout=PAYSTACK_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise ValueError("Unable to contact Paystack. The transaction status is not yet confirmed.") from exc
    try:
        body = response.json()
    except ValueError as exc:
        raise ValueError("Paystack returned an invalid response.") from exc
    if response.status_code >= 500:
        raise ValueError("Paystack is temporarily unavailable. Please retry verification.")
    if response.status_code >= 400 or body.get("status") is not True:
        message = str(body.get("message") or "Paystack request failed.")
        raise ValueError(message[:300])
    data = body.get("data")
    if not isinstance(data, dict) and not isinstance(data, list):
        raise ValueError("Paystack returned an incomplete response.")
    return body


def _verify_transaction_with_paystack(reference: str) -> Dict[str, Any]:
    safe_reference = quote(reference, safe="")
    body = _provider_request("GET", f"transaction/verify/{safe_reference}")
    data = body.get("data")
    if not isinstance(data, dict):
        raise ValueError("Paystack verification response is incomplete.")
    return data


def _validate_verified_transaction(payment: Payment, data: Dict[str, Any]) -> None:
    if data.get("reference") != payment.reference:
        raise ValueError("Paystack transaction reference does not match this payment.")
    if str(data.get("currency", "")).upper() != payment.currency:
        raise ValueError("Paystack transaction currency does not match this payment.")
    try:
        provider_amount = int(data.get("amount"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Paystack transaction amount is invalid.") from exc
    expected_amount = int((Decimal(payment.amount) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if provider_amount != expected_amount:
        raise ValueError("Paystack transaction amount does not match the order total.")


def _record_status_change(db: Session, payment: Payment, new_status: PaymentStatus, source: str, note: Optional[str] = None) -> None:
    old_status = payment.status
    if old_status == new_status:
        return
    payment.status = new_status
    db.add(PaymentStatusHistory(
        payment_id=payment.id, previous_status=old_status.value,
        new_status=new_status.value, source=source, note=note,
    ))


def _apply_verified_transaction(db: Session, payment: Payment, data: Dict[str, Any], source: str) -> str:
    _validate_verified_transaction(payment, data)
    provider_status = str(data.get("status", "")).lower()
    locked_payment = db.scalar(select(Payment).where(Payment.id == payment.id).with_for_update())
    if locked_payment is None:
        raise ValueError("Payment not found.")
    order = db.scalar(select(Order).where(Order.id == locked_payment.order_id).with_for_update())
    if provider_status == "success":
        if locked_payment.status != PaymentStatus.SUCCESS:
            _record_status_change(db, locked_payment, PaymentStatus.SUCCESS, source)
        locked_payment.provider_transaction_id = str(data.get("id")) if data.get("id") is not None else locked_payment.provider_transaction_id
        paid_at = data.get("paid_at") or data.get("transaction_date")
        if isinstance(paid_at, str):
            try:
                locked_payment.paid_at = datetime.fromisoformat(paid_at.replace("Z", "+00:00"))
            except ValueError:
                locked_payment.paid_at = datetime.now(timezone.utc)
        elif locked_payment.paid_at is None:
            locked_payment.paid_at = datetime.now(timezone.utc)
        locked_payment.failure_reason = None
        if order is not None and order.status == OrderStatus.PENDING:
            update_order_status(db, order, OrderStatus.PAID, actor=(
                OrderStatusTransitionActor.PAYMENT_WEBHOOK if source == "webhook"
                else OrderStatusTransitionActor.PAYMENT_FALLBACK_VERIFICATION
            ))
        else:
            db.commit()
        return "success"
    if provider_status in {"failed", "abandoned", "reversed"}:
        if locked_payment.status != PaymentStatus.SUCCESS:
            reason = str(data.get("gateway_response") or provider_status)[:500]
            _record_status_change(db, locked_payment, PaymentStatus.FAILED, source, reason)
            locked_payment.failure_reason = reason
            db.commit()
        return provider_status
    db.commit()
    return provider_status or "unknown"


def initialize_paystack_payment(
    db: Session, *, order_id: int, user: Optional[User],
    guest_access_token: Optional[str] = None, callback_url: Optional[str] = None,
) -> Dict[str, Any]:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise ValueError("Order not found.")
    if user is not None:
        if order.user_id != user.id:
            raise ValueError("Not enough permissions.")
        payer_email = user.email
    else:
        supplied_hash = hashlib.sha256((guest_access_token or "").encode()).hexdigest()
        if (order.user_id is not None or not order.guest_access_token_hash
            or not order.guest_access_token_expires_at
            or order.guest_access_token_expires_at <= datetime.now(timezone.utc)
            or not secrets.compare_digest(supplied_hash, order.guest_access_token_hash)):
            raise ValueError("A valid guest checkout token is required.")
        payer_email = order.customer_email
    if not payer_email:
        raise ValueError("A customer email address is required for payment.")
    if order.status != OrderStatus.PENDING:
        raise ValueError("Only pending orders can be initialized for payment.")

    payment = _get_or_create_payment_for_order(db, order)
    if payment.status == PaymentStatus.SUCCESS:
        raise ValueError("This order has already been paid.")
    if payment.status == PaymentStatus.FAILED:
        raise ValueError("This payment attempt failed. Create a new order to retry payment.")
    if payment.authorization_url and payment.access_code:
        db.commit()
        return {"payment": payment, "authorization_url": payment.authorization_url, "access_code": payment.access_code, "reference": payment.reference}

    payload: Dict[str, Any] = {
        "email": payer_email,
        "amount": int((Decimal(order.total_amount) * 100).quantize(Decimal("1"))),
        "currency": payment.currency,
        "reference": payment.reference,
    }
    if callback_url:
        payload["callback_url"] = callback_url
    try:
        response = _provider_request("POST", "transaction/initialize", payload=payload)
    except ValueError:
        db.commit()
        raise
    data = response["data"]
    if not data.get("authorization_url") or not data.get("access_code") or data.get("reference") != payment.reference:
        db.commit()
        raise ValueError("Paystack returned an invalid initialization response.")
    payment.authorization_url = data["authorization_url"]
    payment.access_code = data["access_code"]
    db.commit()
    db.refresh(payment)
    schedule_payment_verification_fallback(payment.reference)
    logger.info("Paystack payment initialized", extra={"event": "payment_initialized", "order_id": order.id, "payment_id": payment.id, "reference": payment.reference})
    return {"payment": payment, "authorization_url": payment.authorization_url, "access_code": payment.access_code, "reference": payment.reference}


def verify_paystack_webhook_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    settings = get_settings()
    if not settings.PAYSTACK_SECRET_KEY or not signature:
        return False
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_payment_and_reconcile(db: Session, reference: str) -> Tuple[Payment, str]:
    payment = get_payment_by_reference(db, reference)
    if payment is None:
        raise ValueError("Payment not found.")
    data = _verify_transaction_with_paystack(reference)
    result = _apply_verified_transaction(db, payment, data, "manual_verification")
    db.refresh(payment)
    return payment, result


def handle_paystack_webhook_event(db: Session, raw_body: bytes) -> Tuple[bool, str]:
    try:
        event = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, "invalid_payload"
    if not isinstance(event, dict):
        return False, "invalid_payload"
    event_type = str(event.get("event") or "unknown")[:100]
    payload = event.get("data") or {}
    reference = payload.get("reference") if isinstance(payload, dict) else None
    if event_type in {"refund.processed", "refund.failed"} and isinstance(payload, dict):
        event_key = hashlib.sha256(raw_body).hexdigest()
        event_row = db.scalar(select(PaymentEvent).where(
            PaymentEvent.provider == PaymentProvider.PAYSTACK,
            PaymentEvent.event_key == event_key,
        ).with_for_update())
        if event_row is not None and event_row.processing_status in {"processed", "ignored"}:
            return True, "duplicate_event"
        refund_reference = payload.get("reference")
        refund = db.scalar(select(PaymentRefund).where(PaymentRefund.reference == refund_reference).with_for_update()) if refund_reference else None
        if event_row is None:
            event_row = PaymentEvent(provider=PaymentProvider.PAYSTACK, event_key=event_key, event_type=event_type, payment_reference=None, payload_hash=event_key, processing_status="received")
            db.add(event_row)
        if refund is None:
            event_row.processing_status = "ignored"
            event_row.error_message = "Refund reference not found."
            event_row.processed_at = datetime.now(timezone.utc)
            db.commit()
            return True, "refund_not_found"
        if event_type == "refund.processed" and refund.status != "processed":
            refund.status = "processed"
            refund.processed_at = datetime.now(timezone.utc)
            payment = db.scalar(select(Payment).where(Payment.id == refund.payment_id).with_for_update())
            if payment is not None:
                payment.amount_refunded = (Decimal(payment.amount_refunded or 0) + Decimal(refund.amount)).quantize(Decimal("0.01"))
        elif event_type == "refund.failed":
            refund.status = "failed"
        event_row.processing_status = "processed"
        event_row.processed_at = datetime.now(timezone.utc)
        db.commit()
        return True, "refund_updated"
    event_key = hashlib.sha256(raw_body).hexdigest()
    existing = db.scalar(select(PaymentEvent).where(
        PaymentEvent.provider == PaymentProvider.PAYSTACK,
        PaymentEvent.event_key == event_key,
    ).with_for_update())
    if existing is not None and existing.processing_status in {"processed", "ignored"}:
        return True, "duplicate_event"
    if event_type != "charge.success" or not reference:
        if existing is None:
            existing = PaymentEvent(provider=PaymentProvider.PAYSTACK, event_key=event_key, event_type=event_type, payment_reference=reference, payload_hash=event_key, processing_status="ignored", processed_at=datetime.now(timezone.utc))
            db.add(existing)
        else:
            existing.processing_status = "ignored"
            existing.processed_at = datetime.now(timezone.utc)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        return True, "ignored_event"
    try:
        verified = _verify_transaction_with_paystack(str(reference))
    except ValueError as exc:
        if existing is None:
            existing = PaymentEvent(provider=PaymentProvider.PAYSTACK, event_key=event_key, event_type=event_type, payment_reference=str(reference), payload_hash=event_key, processing_status="failed", error_message=str(exc)[:500])
            db.add(existing)
        else:
            existing.processing_status = "failed"
            existing.error_message = str(exc)[:500]
        db.commit()
        return False, "verification_unavailable"
    payment = get_payment_by_reference(db, str(reference))
    if payment is None:
        if existing is None:
            existing = PaymentEvent(provider=PaymentProvider.PAYSTACK, event_key=event_key, event_type=event_type, payment_reference=str(reference), payload_hash=event_key, processing_status="ignored", error_message="Payment reference not found.", processed_at=datetime.now(timezone.utc))
            db.add(existing)
        else:
            existing.processing_status = "ignored"
            existing.error_message = "Payment reference not found."
            existing.processed_at = datetime.now(timezone.utc)
        db.commit()
        return True, "payment_not_found"
    if existing is None:
        existing = PaymentEvent(provider=PaymentProvider.PAYSTACK, event_key=event_key, event_type=event_type, payment_reference=str(reference), payload_hash=event_key, processing_status="received")
        db.add(existing)
    try:
        result = _apply_verified_transaction(db, payment, verified, "webhook")
        existing.processing_status = "processed"
        existing.processed_at = datetime.now(timezone.utc)
        existing.error_message = None
        db.commit()
        return True, f"verified_{result}"
    except ValueError as exc:
        existing.processing_status = "ignored"
        existing.error_message = str(exc)[:500]
        existing.processed_at = datetime.now(timezone.utc)
        db.commit()
        logger.warning("Paystack webhook verification rejected", extra={"event": "payment_webhook_rejected", "reference": str(reference), "reason": str(exc)})
        return True, "verification_mismatch"
    except IntegrityError:
        db.rollback()
        return True, "duplicate_event"


def initiate_paystack_refund(db: Session, *, payment_reference: str, amount: Optional[Decimal], reason: Optional[str], initiated_by: Optional[str]) -> PaymentRefund:
    payment = db.scalar(select(Payment).where(Payment.reference == payment_reference).with_for_update())
    if payment is None:
        raise ValueError("Payment not found.")
    if payment.status != PaymentStatus.SUCCESS:
        raise ValueError("Only successful payments can be refunded.")
    reserved = sum((r.amount for r in db.scalars(select(PaymentRefund).where(PaymentRefund.payment_id == payment.id, PaymentRefund.status != "failed")).all()), Decimal("0.00"))
    remaining = (Decimal(payment.amount) - Decimal(payment.amount_refunded or 0) - reserved).quantize(Decimal("0.01"))
    refund_amount = (amount if amount is not None else remaining).quantize(Decimal("0.01"))
    if refund_amount <= 0 or refund_amount > remaining:
        raise ValueError("Refund amount exceeds the remaining refundable balance.")
    refund_reference = f"qls_{secrets.token_hex(12)}"
    refund = PaymentRefund(payment_id=payment.id, reference=refund_reference, amount=refund_amount, currency=payment.currency, status="pending", reason=reason, initiated_by=initiated_by)
    db.add(refund)
    db.commit()
    payload = {
        "transaction": payment.reference,
        "amount": int((refund_amount * 100).quantize(Decimal("1"))),
        "currency": payment.currency,
        "reference": refund_reference,
        "merchant_note": (reason or "Qless customer refund")[:500],
    }
    try:
        response = _provider_request("POST", "refund", payload=payload)
    except ValueError as exc:
        refund.status = "pending_unknown"
        refund.reason = f"{(reason or 'Refund')[:350]} | Provider outcome unknown: {str(exc)[:120]}"
        db.commit()
        raise ValueError("Refund request outcome is uncertain. Reconcile it with Paystack before retrying.") from exc
    data = response["data"]
    provider_status = str(data.get("status") or "pending").lower().replace("-", "_")
    refund.status = provider_status if provider_status in {"pending", "processing", "processed", "failed", "needs_attention"} else "pending"
    refund.provider_refund_id = str(data.get("id")) if data.get("id") is not None else None
    if refund.status == "processed":
        refund.processed_at = datetime.now(timezone.utc)
        payment.amount_refunded = (Decimal(payment.amount_refunded or 0) + refund_amount).quantize(Decimal("0.01"))
    db.commit()
    db.refresh(refund)
    return refund
