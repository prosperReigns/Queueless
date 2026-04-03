"""Order service logic."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
import logging
import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.store import Store
from app.schemas.order import OrderCreate
from app.services.websocket_service import publish_customer_status_update, publish_merchant_new_order
from app.tasks.notifications import queue_order_notification
from app.tasks.orders import schedule_order_expiry

logger = logging.getLogger(__name__)


class OrderStatusTransitionActor(str, Enum):
    """Actor initiating an order status transition."""

    MERCHANT = "merchant"
    PAYMENT_WEBHOOK = "payment_webhook"
    PAYMENT_FALLBACK_VERIFICATION = "payment_fallback_verification"
    SYSTEM = "system"


_ALLOWED_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.PREPARING},
    OrderStatus.PREPARING: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.COMPLETED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}

_ACTOR_ALLOWED_TRANSITIONS: dict[OrderStatusTransitionActor, dict[OrderStatus, set[OrderStatus]]] = {
    OrderStatusTransitionActor.PAYMENT_WEBHOOK: {
        OrderStatus.PENDING: {OrderStatus.PAID},
    },
    OrderStatusTransitionActor.PAYMENT_FALLBACK_VERIFICATION: {
        OrderStatus.PENDING: {OrderStatus.PAID},
    },
    OrderStatusTransitionActor.MERCHANT: {
        OrderStatus.PAID: {OrderStatus.PREPARING},
        OrderStatus.PREPARING: {OrderStatus.READY},
        OrderStatus.READY: {OrderStatus.COMPLETED},
    },
    OrderStatusTransitionActor.SYSTEM: {
        OrderStatus.PENDING: {OrderStatus.CANCELLED},
    },
}


def emit_order_status_side_effects(order: Order, *, notification_event: str | None = None) -> None:
    """Emit notification and websocket side effects for an order status change."""
    event = notification_event or f"order_status_{order.status.value}"
    queue_order_notification(order.id, event)
    publish_customer_status_update(order.user_id, order)


def get_order_by_id(db: Session, order_id: int) -> Order | None:
    """Return an order by id with items eagerly loaded."""
    stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    return db.scalar(stmt)


def list_orders(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    store_ids: list[int] | None = None,
    status: OrderStatus | None = None,
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> list[Order]:
    """Return orders with optional scope, filtering, pagination, and sorting."""
    stmt: Select[tuple[Order]] = select(Order).options(selectinload(Order.items))

    if user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)
    if store_ids is not None:
        if not store_ids:
            return []
        stmt = stmt.where(Order.store_id.in_(store_ids))
    if status is not None:
        stmt = stmt.where(Order.status == status)

    sortable_columns = {
        "created_at": Order.created_at,
        "id": Order.id,
        "total_amount": Order.total_amount,
        "status": Order.status,
    }
    sort_column = sortable_columns.get(sort_by, Order.created_at)
    stmt = stmt.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc(), Order.id.desc())
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def validate_order_status_transition(
    order: Order,
    status: OrderStatus,
    *,
    actor: OrderStatusTransitionActor,
) -> None:
    """Validate an order status transition for a specific actor."""
    actor_allowed_next_statuses = _ACTOR_ALLOWED_TRANSITIONS.get(actor, {}).get(order.status, set())
    if status not in actor_allowed_next_statuses:
        logger.warning(
            "Order status update failed: actor not allowed for transition.",
            extra={
                "event": "order_status_update_failed",
                "order_id": order.id,
                "from_status": order.status.value,
                "to_status": status.value,
                "actor": actor.value,
                "reason": "actor_forbidden_transition",
            },
        )
        raise ValueError(
            f"{actor.value} cannot perform order status transition: "
            f"{order.status.value} -> {status.value}."
        )

    allowed_next_statuses = _ALLOWED_STATUS_TRANSITIONS.get(order.status, set())
    if status not in allowed_next_statuses:
        logger.warning(
            "Order status update failed: invalid transition.",
            extra={
                "event": "order_status_update_failed",
                "order_id": order.id,
                "from_status": order.status.value,
                "to_status": status.value,
                "actor": actor.value,
                "reason": "invalid_transition",
            },
        )
        raise ValueError(
            f"Invalid order status transition for {actor.value}: "
            f"{order.status.value} -> {status.value}."
        )


def create_order(db: Session, payload: OrderCreate, user_id: uuid.UUID) -> Order:
    """Create an order with line items and computed total amount."""
    store = db.get(Store, payload.store_id)
    if store is None or not store.is_active:
        logger.warning(
            "Order creation failed: store missing or inactive.",
            extra={
                "event": "order_creation_failed",
                "user_id": str(user_id),
                "store_id": payload.store_id,
                "reason": "store_missing_or_inactive",
            },
        )
        raise ValueError("Store not found or inactive.")

    product_ids = [item.product_id for item in payload.items]
    stmt = select(Product).where(Product.id.in_(product_ids), Product.store_id == payload.store_id)
    products = list(db.scalars(stmt).all())
    product_by_id = {product.id: product for product in products}

    order_items: list[OrderItem] = []
    total_amount = Decimal("0.00")

    for item in payload.items:
        product = product_by_id.get(item.product_id)
        if product is None:
            logger.warning(
                "Order creation failed: product not found in store.",
                extra={
                    "event": "order_creation_failed",
                    "user_id": str(user_id),
                    "store_id": payload.store_id,
                    "product_id": item.product_id,
                    "reason": "product_not_found_in_store",
                },
            )
            raise ValueError(f"Product {item.product_id} not found in this store.")
        if not product.is_available:
            logger.warning(
                "Order creation failed: product unavailable.",
                extra={
                    "event": "order_creation_failed",
                    "user_id": str(user_id),
                    "store_id": payload.store_id,
                    "product_id": item.product_id,
                    "reason": "product_unavailable",
                },
            )
            raise ValueError(f"Product {item.product_id} is not available.")

        line_price = Decimal(product.price)
        order_items.append(
            OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                price=line_price,
            )
        )
        total_amount += line_price * item.quantity

    order = Order(
        user_id=user_id,
        store_id=payload.store_id,
        total_amount=total_amount.quantize(Decimal("0.01")),
        status=OrderStatus.PENDING,
        payment_reference=str(uuid.uuid4()),
        items=order_items,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    schedule_order_expiry(order.id)
    queue_order_notification(order.id, "order_created")
    publish_merchant_new_order(store.owner_id, order)
    logger.info(
        "Order created.",
        extra={
            "event": "order_created",
            "order_id": order.id,
            "user_id": str(order.user_id),
            "store_id": order.store_id,
            "status": order.status.value,
            "total_amount": str(order.total_amount),
            "item_count": len(order.items),
        },
    )
    return order


def update_order_status(
    db: Session,
    order: Order,
    status: OrderStatus,
    *,
    actor: OrderStatusTransitionActor,
    commit: bool = True,
    emit_side_effects: bool = True,
) -> Order:
    """Update an order status if the transition is valid.

    When ``commit`` is False, caller manages transaction boundaries and refreshes.
    When ``emit_side_effects`` is False, notifications/websocket publishing are skipped.
    """
    if order.status == status:
        logger.info(
            "Order status update skipped: unchanged status.",
            extra={
                "event": "order_status_unchanged",
                "order_id": order.id,
                "actor": actor.value,
                "status": order.status.value,
            },
        )
        return order

    previous_status = order.status
    validate_order_status_transition(order, status, actor=actor)

    order.status = status
    db.add(order)
    if commit:
        db.commit()
        db.refresh(order)
    if emit_side_effects:
        emit_order_status_side_effects(order)
    logger.info(
        "Order status updated.",
        extra={
            "event": "order_status_updated",
            "order_id": order.id,
            "actor": actor.value,
            "user_id": str(order.user_id),
            "store_id": order.store_id,
            "from_status": previous_status.value,
            "to_status": order.status.value,
        },
    )
    return order
