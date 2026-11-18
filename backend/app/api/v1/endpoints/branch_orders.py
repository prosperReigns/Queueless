"""Branch-aware customer order creation and branch-scoped order access."""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.api.deps import get_db, get_optional_current_user, get_current_active_user
from app.core.config import get_settings
from app.core.rate_limiter import limiter
from app.models.user import User, UserRole
from app.models.business_membership import BusinessRole
from app.models.branch import Branch
from app.models.order import Order, OrderStatus
from app.services.business_service import get_membership
from app.services.branch_order_service import create_branch_order
from app.schemas.branch_order import BranchOrderCreate

router = APIRouter(tags=["branch-orders"])
settings = get_settings()

@router.post("/orders/branch", status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_ORDER_CREATE)
def create_branch_order_endpoint(
    request: Request,
    payload: BranchOrderCreate,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    """Create a preorder or onsite QR order; guests receive a time-limited checkout token."""
    if user is not None and user.role not in (UserRole.CUSTOMER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Customer account required.")
    try:
        order, guest_token = create_branch_order(db, payload, user.id if user else None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": order.id,
        "branch_id": order.branch_id,
        "order_source": order.order_source.value,
        "fulfillment_method": order.fulfillment_method.value,
        "scheduled_for": order.scheduled_for,
        "total_amount": order.total_amount,
        "status": order.status.value,
        "payment_reference": order.payment_reference,
        "guest_access_token": guest_token,
    }


@router.get("/customers/me/branch-orders")
def list_my_branch_orders(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """List the authenticated customer's Qless branch orders without mixing legacy store schemas."""
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Customer account required.")
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id, Order.branch_id.is_not(None))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset(skip)
        .limit(limit)
    )
    orders = db.scalars(stmt).all()
    return [{
        "id": order.id,
        "branch_id": str(order.branch_id),
        "order_source": order.order_source.value if order.order_source else None,
        "fulfillment_method": order.fulfillment_method.value if order.fulfillment_method else None,
        "customer_name": order.customer_name,
        "total_amount": str(order.total_amount),
        "status": order.status.value,
        "created_at": order.created_at,
        "items": [{
            "item_name": item.item_name,
            "quantity": item.quantity,
            "unit_price": str(item.price),
        } for item in order.items],
    } for order in orders]

@router.get("/branches/{branch_id}/orders")
def list_branch_orders(
    branch_id: uuid.UUID,
    status_filter: Optional[OrderStatus] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    """List orders for one branch; branch membership is checked server-side."""
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found.")
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if user.role != UserRole.ADMIN:
        membership = get_membership(db, user.id, branch.business_id, branch.id)
        if membership is None or membership.role not in {
            BusinessRole.OWNER, BusinessRole.FRANCHISE_ADMIN, BusinessRole.BRANCH_MANAGER
        }:
            raise HTTPException(status_code=403, detail="Branch reporting access denied.")
    stmt = select(Order).options(selectinload(Order.items)).where(Order.branch_id == branch_id)
    if status_filter is not None:
        stmt = stmt.where(Order.status == status_filter)
    orders = db.scalars(stmt.order_by(Order.created_at.desc(), Order.id.desc()).offset(skip).limit(limit)).all()
    return [{
        "id": order.id,
        "branch_id": order.branch_id,
        "order_source": order.order_source.value if order.order_source else None,
        "fulfillment_method": order.fulfillment_method.value if order.fulfillment_method else None,
        "scheduled_for": order.scheduled_for,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "customer_phone": order.customer_phone,
        "total_amount": order.total_amount,
        "status": order.status.value,
        "payment_reference": order.payment_reference,
        "created_at": order.created_at,
        "items": [{
            "menu_item_id": item.menu_item_id,
            "item_name": item.item_name,
            "quantity": item.quantity,
            "unit_price": item.price,
            "line_total": item.price * item.quantity,
        } for item in order.items],
    } for order in orders]
