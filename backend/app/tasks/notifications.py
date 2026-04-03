"""Background tasks related to notifications."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import firebase_admin
import httpx
from celery.exceptions import CeleryError
from firebase_admin import credentials, messaging
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.order import Order
from app.models.store import Store
from app.models.user import User
from app.services.notification_token_service import (
    delete_notification_tokens_by_values,
    list_user_notification_tokens,
)
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificationTarget:
    """Resolved recipient metadata for a notification event."""

    user_id: str
    role: str
    fcm_tokens: list[str]
    phone_number: str | None


@dataclass(slots=True)
class OrderContext:
    """Order data needed for notification routing/content."""

    order_id: int
    store_id: int
    user_id: str


@dataclass(slots=True)
class SmsFallbackResult:
    """SMS fallback outcome."""

    was_attempted: bool
    was_delivered: bool


def _normalize_phone_number(phone_number: str | None) -> str | None:
    """Normalize phone number for SMS provider, keeping leading + when provided."""
    if phone_number is None:
        return None
    normalized = phone_number.strip()
    return normalized or None


def _initialize_firebase_app() -> firebase_admin.App | None:
    """Initialize Firebase app once if credentials are configured."""
    settings = get_settings()
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    cred: credentials.Base | None = None
    if settings.FIREBASE_CREDENTIALS_JSON:
        try:
            cred_payload = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_payload)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Invalid FIREBASE_CREDENTIALS_JSON payload.", exc_info=exc)
            return None
    elif settings.FIREBASE_CREDENTIALS_PATH:
        path = Path(settings.FIREBASE_CREDENTIALS_PATH)
        if not path.exists():
            logger.error("Firebase credentials file not found: %s", path)
            return None
        cred = credentials.Certificate(str(path))

    if cred is None:
        logger.info("Firebase credentials are not configured; skipping FCM.")
        return None

    return firebase_admin.initialize_app(cred)


@lru_cache
def _get_phone_number_column_name() -> str | None:
    """Return available optional users phone number column."""
    with SessionLocal() as db:
        columns_stmt = text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :table_schema
              AND table_name = :table_name
              AND column_name IN ('phone_number')
            """
        )
        columns = {
            row[0]
            for row in db.execute(
                columns_stmt,
                {"table_schema": "public", "table_name": "users"},
            )
        }
        return "phone_number" if "phone_number" in columns else None


def _get_optional_user_phone_number(recipient_id: Any) -> str | None:
    """Read optional user phone number when that column exists in DB."""
    phone_number_col = _get_phone_number_column_name()
    if not phone_number_col:
        return None
    with SessionLocal() as db:
        stmt = text("SELECT phone_number FROM users WHERE id = :user_id")
        result = db.execute(stmt, {"user_id": recipient_id}).mappings().first()
        if result is None:
            return None
        return _normalize_phone_number(result.get("phone_number"))


def _resolve_notification_target(order: OrderContext, event: str) -> NotificationTarget | None:
    """Resolve recipient by event type."""
    with SessionLocal() as db:
        if event == "order_created":
            store = db.get(Store, order.store_id)
            if store is None:
                return None
            recipient = db.get(User, store.owner_id)
            role = "merchant"
        elif event == "order_status_ready":
            recipient = db.get(User, order.user_id)
            role = "customer"
        else:
            return None

        if recipient is None:
            return None

        notification_tokens = list_user_notification_tokens(db, recipient.id)
        phone_number = _get_optional_user_phone_number(recipient.id)

        return NotificationTarget(
            user_id=str(recipient.id),
            role=role,
            fcm_tokens=[token_record.token for token_record in notification_tokens],
            phone_number=phone_number,
        )


def _build_notification_content(order: OrderContext, event: str) -> tuple[str, str]:
    """Build user-facing notification title/body."""
    if event == "order_created":
        return (
            "New order received",
            f"Order #{order.order_id} has been created and is awaiting processing.",
        )
    if event == "order_status_ready":
        return (
            "Order ready for pickup",
            f"Your order #{order.order_id} is ready for pickup.",
        )
    return ("Order update", f"Order #{order.order_id} has an update.")


def _send_fcm_notification(*, token: str, title: str, body: str, data: dict[str, str]) -> str:
    """Send FCM push notification if Firebase is configured."""
    app = _initialize_firebase_app()
    if app is None:
        return "failed"
    try:
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=data,
        )
        messaging.send(message, app=app)
        return "sent"
    except messaging.UnregisteredError as exc:
        logger.info("FCM token is unregistered; push notification dropped.", exc_info=exc)
        return "unregistered"
    except messaging.QuotaExceededError as exc:
        logger.warning("FCM quota exceeded while sending notification.", exc_info=exc)
        return "failed"
    except ValueError as exc:
        logger.warning("FCM message payload was invalid.", exc_info=exc)
        return "failed"
    except firebase_admin.exceptions.FirebaseError as exc:
        logger.warning("Firebase error while sending FCM notification.", exc_info=exc)
        return "failed"


def _should_send_sms(event: str) -> bool:
    """Determine whether SMS should be sent for event."""
    settings = get_settings()
    if event == "order_created":
        return True
    if event == "order_status_ready":
        return settings.TERMII_SEND_ORDER_READY_SMS
    return False


def _send_termii_sms(*, phone_number: str, message: str) -> bool:
    """Send SMS using Termii API."""
    settings = get_settings()
    if not settings.TERMII_API_KEY:
        logger.info("TERMII_API_KEY not configured; skipping SMS.")
        return False

    payload = {
        "api_key": settings.TERMII_API_KEY,
        "to": phone_number,
        "from": settings.TERMII_SENDER_ID,
        "sms": message,
        "type": "plain",
        "channel": settings.TERMII_CHANNEL,
    }
    try:
        response = httpx.post(
            f"{settings.TERMII_BASE_URL.rstrip('/')}/api/sms/send",
            json=payload,
            timeout=settings.TERMII_TIMEOUT_SECONDS,
        )
    except httpx.RequestError as exc:
        logger.warning("Failed to send SMS via Termii due to network error.", exc_info=exc)
        return False

    if response.status_code >= 400:
        logger.warning(
            "Termii rejected SMS request with status=%s body=%s.",
            response.status_code,
            response.text,
        )
        return False

    try:
        body: dict[str, Any] = response.json()
    except ValueError:
        logger.warning("Termii returned non-JSON SMS response.")
        return False

    # Termii responses vary by route/version; accept common success markers:
    # "code": "ok" (API v1), "message_id" present, or "status": "success"/"ok".
    if body.get("code") == "ok":
        return True
    if body.get("message_id"):
        return True
    status = body.get("status")
    if isinstance(status, str) and status.lower() in {"success", "ok"}:
        return True

    logger.warning("Termii SMS response did not indicate success.")
    return False


def _attempt_sms_fallback(
    *,
    push_sent: bool,
    event: str,
    target: NotificationTarget,
    message: str,
) -> SmsFallbackResult:
    """Attempt SMS fallback and return delivery outcome."""
    if push_sent or not _should_send_sms(event) or not target.phone_number:
        return SmsFallbackResult(was_attempted=False, was_delivered=False)
    return SmsFallbackResult(
        was_attempted=True,
        was_delivered=_send_termii_sms(phone_number=target.phone_number, message=message),
    )


@celery_app.task(
    bind=True,
    name="app.tasks.notifications.send_order_notification_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def send_order_notification_task(self, order_id: int, event: str) -> dict[str, str | int]:  # noqa: ARG001
    """Send order notifications via FCM with Termii SMS fallback."""
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if order is None:
            return {"status": "order_not_found", "order_id": order_id, "event": event}
        order_context = OrderContext(
            order_id=order.id,
            store_id=order.store_id,
            user_id=str(order.user_id),
        )

    target = _resolve_notification_target(order_context, event)
    if target is None:
        return {"status": "event_ignored", "order_id": order_id, "event": event}

    title, body = _build_notification_content(order_context, event)
    data = {"order_id": str(order_context.order_id), "event": event, "recipient_role": target.role}

    push_sent = False
    invalid_tokens: list[str] = []
    for token in target.fcm_tokens:
        result = _send_fcm_notification(token=token, title=title, body=body, data=data)
        if result == "sent":
            push_sent = True
        elif result == "unregistered":
            invalid_tokens.append(token)

    if invalid_tokens:
        with SessionLocal() as db:
            delete_notification_tokens_by_values(db, invalid_tokens)

    sms_result = _attempt_sms_fallback(
        push_sent=push_sent,
        event=event,
        target=target,
        message=body,
    )
    sms_attempted = sms_result.was_attempted
    sms_sent = sms_result.was_delivered

    if push_sent:
        status = "delivered_fcm"
    elif sms_sent:
        status = "delivered_sms"
    elif sms_attempted:
        status = "failed_sms"
    else:
        status = "no_channel"

    logger.info(
        "Order notification delivery completed.",
        extra={
            "event": "order_notification_delivery",
            "order_id": order_context.order_id,
            "notification_event": event,
            "recipient_user_id": target.user_id,
            "recipient_role": target.role,
            "fcm_sent": push_sent,
            "sms_attempted": sms_attempted,
            "sms_sent": sms_sent,
            "status": status,
        },
    )
    return {"status": status, "order_id": order_id, "event": event}


def queue_order_notification(order_id: int, event: str) -> None:
    """Enqueue non-blocking order notification task."""
    try:
        send_order_notification_task.delay(order_id, event)
    except CeleryError as exc:
        logger.warning(
            "Failed to enqueue order notification task.",
            extra={"event": "order_notification_enqueue_failed", "order_id": order_id, "notification_event": event},
            exc_info=exc,
        )
