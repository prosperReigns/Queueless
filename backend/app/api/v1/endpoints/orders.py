"""Order endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    RoleScopeAccess,
    get_current_active_user,
    get_db,
    get_role_scope_access,
    require_roles,
)
from app.models.order import OrderStatus
from app.models.store import Store
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order_service import (
    OrderStatusTransitionActor,
    create_order,
    get_order_by_id,
    list_orders,
    update_order_status,
)
from app.services.store_service import get_store_by_id

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderResponse])
def list_orders_endpoint(
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="created_at", pattern="^(created_at|id|total_amount|status)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrderResponse]:
    """List orders scoped by role with filtering, pagination, and sorting."""
    user_id = None
    store_ids = None

    if current_user.role == UserRole.CUSTOMER:
        user_id = current_user.id
    elif current_user.role == UserRole.MERCHANT:
        store_ids = list(
            db.scalars(select(Store.id).where(Store.owner_id == current_user.id)).all()
        )

    orders = list_orders(
        db,
        user_id=user_id,
        store_ids=store_ids,
        status=status_filter,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return [OrderResponse.model_validate(order) for order in orders]


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order_endpoint(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> OrderResponse:
    """Create a customer order with line items and computed total."""
    try:
        order = create_order(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OrderResponse.model_validate(order)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    role_scope: RoleScopeAccess = Depends(get_role_scope_access),
) -> OrderResponse:
    """Get a single order if authorized."""
    order = get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    store = get_store_by_id(db, order.store_id)
    role_scope.enforce(
        customer_id=order.user_id,
        merchant_owner_id=store.owner_id if store is not None else None,
    )

    return OrderResponse.model_validate(order)


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status_endpoint(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.MERCHANT)),
    role_scope: RoleScopeAccess = Depends(get_role_scope_access),
) -> OrderResponse:
    """Update order status for merchant-owned store orders."""
    order = get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    store = get_store_by_id(db, order.store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    role_scope.enforce(merchant_owner_id=store.owner_id)

    try:
        updated = update_order_status(
            db,
            order,
            payload.status,
            actor=OrderStatusTransitionActor.MERCHANT,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OrderResponse.model_validate(updated)
