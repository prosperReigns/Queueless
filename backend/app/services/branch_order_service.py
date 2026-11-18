"""Unified branch-aware order creation for preorder and onsite QR channels."""
from __future__ import annotations
import hashlib, secrets, uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.branch import Branch
from app.models.branch_qr_code import BranchQRCode
from app.models.menu import MenuItem, BranchMenuItem, MenuCategory
from app.models.order import OrderSource as ORMOrderSource, FulfillmentMethod as ORMFulfillmentMethod
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.tasks.orders import schedule_order_expiry

def create_branch_order(db: Session, payload, user_id=None):
    if payload.scheduled_for is not None:
        if payload.scheduled_for.tzinfo is None or payload.scheduled_for <= datetime.now(timezone.utc):
            raise ValueError("scheduled_for must be a future timezone-aware datetime.")
    if payload.source == "onsite_qr":
        if payload.branch_qr_token is None:
            raise ValueError("Onsite QR orders require a branch QR code.")
        qr = db.scalar(select(BranchQRCode).where(BranchQRCode.token == payload.branch_qr_token, BranchQRCode.is_active.is_(True)))
        branch = db.get(Branch, qr.branch_id) if qr else None
        if branch is None:
            raise ValueError("Branch QR code is invalid.")
    else:
        if payload.branch_id is None:
            raise ValueError("Remote preorders require a selected branch.")
        branch = db.get(Branch, payload.branch_id)
    if branch is None or not branch.is_active or not branch.business.is_active:
        raise ValueError("Branch not found or inactive.")
    ids = [line.menu_item_id for line in payload.items]
    items = list(db.scalars(select(MenuItem).where(MenuItem.id.in_(ids), MenuItem.business_id == branch.business_id, MenuItem.is_active.is_(True))).all())
    by_id = {item.id: item for item in items}
    snapshots, total = [], Decimal("0.00")
    for line in payload.items:
        item = by_id.get(line.menu_item_id)
        if item is None:
            raise ValueError("One or more menu items are unavailable at this branch.")
        if item.category_id is not None:
            category = db.get(MenuCategory, item.category_id)
            if category is None or not category.is_active or category.business_id != branch.business_id:
                raise ValueError(f"{item.name} is not in an active menu category.")
        override = db.scalar(select(BranchMenuItem).where(BranchMenuItem.branch_id == branch.id, BranchMenuItem.menu_item_id == item.id))
        if override is not None and not override.is_available:
            raise ValueError(f"{item.name} is not available at this branch.")
        price = override.price_override if override and override.price_override is not None else item.base_price
        snapshots.append(OrderItem(menu_item_id=item.id, product_id=None, item_name=item.name, quantity=line.quantity, price=price))
        total += price * line.quantity
    guest_token = secrets.token_urlsafe(32) if user_id is None else None
    order = Order(
        user_id=user_id, store_id=None, branch_id=branch.id, order_source=ORMOrderSource(payload.source.value),
        fulfillment_method=ORMFulfillmentMethod(payload.fulfillment_method.value), scheduled_for=payload.scheduled_for,
        customer_name=payload.customer_name, customer_email=payload.customer_email,
        customer_phone=payload.customer_phone,
        guest_access_token_hash=hashlib.sha256(guest_token.encode()).hexdigest() if guest_token else None,
        guest_access_token_expires_at=(datetime.now(timezone.utc) + timedelta(hours=24)) if guest_token else None,
        total_amount=total.quantize(Decimal("0.01")), status=OrderStatus.PENDING,
        payment_reference=str(uuid.uuid4()), items=snapshots,
    )
    db.add(order); db.commit(); db.refresh(order)
    schedule_order_expiry(order.id)
    return order, guest_token
