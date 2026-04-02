"""Background tasks related to order lifecycle."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.order import Order, OrderStatus
from app.tasks.celery_app import celery_app

settings = get_settings()


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
    expires_before = datetime.now(timezone.utc) - timedelta(minutes=settings.ORDER_EXPIRY_MINUTES)
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if order is None:
            return "not_found"
        if order.status != OrderStatus.PENDING:
            return "not_pending"
        created_at = order.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at > expires_before:
            return "not_expired_yet"

        order.status = OrderStatus.CANCELLED
        db.add(order)
        db.commit()
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
    expires_before = datetime.now(timezone.utc) - timedelta(minutes=settings.ORDER_EXPIRY_MINUTES)
    expired_count = 0
    with SessionLocal() as db:
        stmt = select(Order).where(Order.status == OrderStatus.PENDING, Order.created_at <= expires_before)
        stale_orders = list(db.scalars(stmt).all())
        for order in stale_orders:
            order.status = OrderStatus.CANCELLED
            db.add(order)
            expired_count += 1
        if expired_count:
            db.commit()
    return expired_count


def schedule_order_expiry(order_id: int) -> None:
    """Queue delayed task to expire an unpaid order after configured minutes."""
    delay_seconds = settings.ORDER_EXPIRY_MINUTES * 60
    expire_unpaid_order_task.apply_async(args=[order_id], countdown=delay_seconds)
