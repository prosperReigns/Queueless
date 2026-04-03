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
from firebase_admin import credentials, messaging
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.order import Order
from app.models.store import Store
from app.models.user import User
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificationTarget:
    """Resolved recipient metadata for a notification event."""

    user_id: str
    role: str
    fcm_token: str | None
    phone_number: str | None


@dataclass(slots=True)
class OrderContext:
    """Order data needed for notification routing/content."""

    order_id: int
    store_id: int
    user_id: str


def _normalize_phone_number(phone_number: str | None) -> str | None:
    """Normalize phone number for SMS provider, keeping leading + when provided."""
    if phone_number is None:
        return None
    normalized = phone_number.strip()
    return normalized or None


@lru_cache
def _initialize_firebase_app() -> firebase_admin.App | None:
    """Initialize Firebase app once if credentials are configured."""
    settings = get_settings()
    if firebase_admin._apps:
        return firebase_admin.get_app()

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


def _get_optional_user_contact_fields(db_user_id: str) -> tuple[str | None, str | None]:
    """Read optional user contact fields when those columns exist in DB."""
    with SessionLocal() as db:
        columns_stmt = text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name IN ('fcm_token', 'phone_number')
            """
        )
        columns = {row[0] for row in db.execute(columns_stmt)}
        if not columns:
            return (None, None)

        selected = ["id"]
        if "fcm_token" in columns:
            selected.append("fcm_token")
        if "phone_number" in columns:
            selected.append("phone_number")

        stmt = text(f"SELECT {', '.join(selected)} FROM users WHERE id::text = :user_id")
        result = db.execute(stmt, {"user_id": db_user_id}).mappings().first()
        if result is None:
            return (None, None)
        return (
            result.get("fcm_token"),
            _normalize_phone_number(result.get("phone_number")),
        )


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

        fcm_token, phone_number = _get_optional_user_contact_fields(str(recipient.id))

        return NotificationTarget(
            user_id=str(recipient.id),
            role=role,
            fcm_token=fcm_token,
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


def _send_fcm_notification(*, token: str, title: str, body: str, data: dict[str, str]) -> bool:
    """Send FCM push notification if Firebase is configured."""
    app = _initialize_firebase_app()
    if app is None:
        return False
    try:
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=data,
        )
        messaging.send(message, app=app)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to send FCM notification.", exc_info=exc)
        return False


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
    except httpx.HTTPError as exc:
        logger.warning("Failed to send SMS via Termii due to network/provider error.", exc_info=exc)
        return False

    if response.status_code >= 400:
        logger.warning("Termii rejected SMS request with status=%s.", response.status_code)
        return False

    try:
        body: dict[str, Any] = response.json()
    except ValueError:
        logger.warning("Termii returned non-JSON SMS response.")
        return False

    if body.get("code") and str(body.get("code")).startswith("ok"):
        return True
    if body.get("message_id"):
        return True
    if isinstance(body.get("status"), str) and body.get("status", "").lower() in {"success", "ok"}:
        return True

    logger.warning("Termii SMS response did not indicate success.")
    return False


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
    if target.fcm_token:
        push_sent = _send_fcm_notification(token=target.fcm_token, title=title, body=body, data=data)

    sms_attempted = False
    sms_sent = False
    if (not push_sent) and _should_send_sms(event) and target.phone_number:
        sms_attempted = True
        sms_sent = _send_termii_sms(phone_number=target.phone_number, message=body)

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
    send_order_notification_task.delay(order_id, event)
