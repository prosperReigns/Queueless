"""Background tasks related to order lifecycle."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.order import Order, OrderStatus
from app.services.order_service import OrderStatusTransitionSource, update_order_status
from app.tasks.celery_app import celery_app

settings = get_settings()
ORDER_EXPIRY_BATCH_SIZE = 500
SECONDS_PER_MINUTE = 60


def _expiry_cutoff_utc() -> datetime:
    """Return UTC cutoff datetime for unpaid order expiry."""
    return datetime.now(timezone.utc) - timedelta(minutes=settings.ORDER_EXPIRY_MINUTES)


def _as_utc(value: datetime) -> datetime:
    """Normalize datetime to UTC-aware."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@celery_app.task(
    bind=True,
    name="app.tasks.orders.expire_unpaid_order_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def expire_unpaid_order_task(self, order_id: int) -> str:  # noqa: ARG001
    """Cancel a pending order that remains unpaid past expiry window."""
    expires_before = _expiry_cutoff_utc()
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if order is None:
            return "not_found"
        if order.status != OrderStatus.PENDING:
            return "not_pending"
        if _as_utc(order.created_at) > expires_before:
            return "not_expired_yet"

        update_order_status(
            db,
            order,
            OrderStatus.CANCELLED,
            source=OrderStatusTransitionSource.SYSTEM,
        )
        return "expired"


@celery_app.task(
    bind=True,
    name="app.tasks.orders.expire_pending_orders_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def expire_pending_orders_task(self) -> int:  # noqa: ARG001
    """Bulk-cancel all pending unpaid orders older than expiry window."""
    expires_before = _expiry_cutoff_utc()
    expired_count = 0
    last_seen_id = 0
    while True:
        with SessionLocal() as db:
            stmt = (
                select(Order)
                .where(Order.status == OrderStatus.PENDING, Order.id > last_seen_id)
                .order_by(Order.id)
                .limit(ORDER_EXPIRY_BATCH_SIZE)
            )
            pending_orders = db.scalars(stmt).all()
            if not pending_orders:
                break
            for order in pending_orders:
                if _as_utc(order.created_at) <= expires_before:
                    update_order_status(
                        db,
                        order,
                        OrderStatus.CANCELLED,
                        source=OrderStatusTransitionSource.SYSTEM,
                    )
                    expired_count += 1
                last_seen_id = order.id
            db.commit()
    return expired_count


def schedule_order_expiry(order_id: int) -> None:
    """Queue delayed task to expire an unpaid order after configured minutes."""
    delay_seconds = settings.ORDER_EXPIRY_MINUTES * SECONDS_PER_MINUTE
    expire_unpaid_order_task.apply_async(args=[order_id], countdown=delay_seconds)
