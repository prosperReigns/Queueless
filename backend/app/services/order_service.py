"""Order service logic."""

from __future__ import annotations

from decimal import Decimal
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.store import Store
from app.schemas.order import OrderCreate

_ALLOWED_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.PREPARING},
    OrderStatus.PREPARING: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.COMPLETED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


def get_order_by_id(db: Session, order_id: int) -> Order | None:
    """Return an order by id with items eagerly loaded."""
    stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    return db.scalar(stmt)


def create_order(db: Session, payload: OrderCreate, user_id: uuid.UUID) -> Order:
    """Create an order with line items and computed total amount."""
    store = db.get(Store, payload.store_id)
    if store is None or not store.is_active:
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
            raise ValueError(f"Product {item.product_id} not found in this store.")
        if not product.is_available:
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
    return order


def update_order_status(db: Session, order: Order, status: OrderStatus) -> Order:
    """Update an order status if the transition is valid."""
    if order.status == status:
        return order

    allowed_next_statuses = _ALLOWED_STATUS_TRANSITIONS[order.status]
    if status not in allowed_next_statuses:
        raise ValueError(
            f"Invalid order status transition: {order.status.value} -> {status.value}."
        )

    order.status = status
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
