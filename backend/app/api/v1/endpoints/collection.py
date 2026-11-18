"""Customer collection credential issuance and branch handoff redemption."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_user, get_db, get_optional_current_user
from app.core.rate_limiter import limiter
from app.models.branch import Branch
from app.models.business_membership import BusinessRole
from app.models.fulfillment import FulfillmentStatus
from app.models.kitchen import KitchenTicket
from app.models.order import Order
from app.models.user import User, UserRole
from app.schemas.fulfillment import CollectionCredentialIssueRequest, CollectionCredentialResponse, CollectionRedemptionRequest, FulfillmentTrackingResponse
from app.services.business_service import get_membership
from app.services.fulfillment_service import get_order_fulfillment, issue_collection_credential, redeem_collection_credential
from app.services.payment_service import has_valid_guest_checkout_token

router = APIRouter(tags=["collection"])
_COLLECTION_ROLES = {BusinessRole.OWNER, BusinessRole.FRANCHISE_ADMIN, BusinessRole.BRANCH_MANAGER, BusinessRole.COLLECTION_STAFF}

def _authorize_customer_order(order: Order, user: User | None, guest_token: str | None) -> None:
    if user is not None and user.role == UserRole.CUSTOMER and order.user_id == user.id:
        return
    if has_valid_guest_checkout_token(order, guest_token):
        return
    raise HTTPException(status_code=403, detail="Valid order owner credentials are required.")

def _authorize_collection_branch(db: Session, user: User, branch: Branch) -> None:
    if user.role == UserRole.ADMIN:
        return
    membership = get_membership(db, user.id, branch.business_id, branch.id)
    if membership is None or membership.role not in _COLLECTION_ROLES:
        raise HTTPException(status_code=403, detail="Collection access denied for this branch.")

@router.get("/orders/{order_id}/tracking", response_model=FulfillmentTrackingResponse)
def get_order_tracking(order_id: int, x_guest_access_token: str | None = Header(default=None), db: Session = Depends(get_db), user: User | None = Depends(get_optional_current_user)):
    order = db.scalar(select(Order).where(Order.id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    _authorize_customer_order(order, user, x_guest_access_token)
    ticket = db.scalar(select(KitchenTicket).where(KitchenTicket.order_id == order.id))
    fulfillment = get_order_fulfillment(db, order.id)
    return FulfillmentTrackingResponse(
        order_id=order.id, order_status=order.status.value,
        kitchen_status=ticket.status if ticket else None,
        fulfillment_method=fulfillment.method if fulfillment else (order.fulfillment_method.value if order.fulfillment_method else None),
        fulfillment_status=fulfillment.status if fulfillment else None,
        branch_id=str(order.branch_id) if order.branch_id else None,
        scheduled_for=order.scheduled_for,
        updated_at=fulfillment.updated_at if fulfillment else None,
    )

@router.post("/orders/{order_id}/collection-credential", response_model=CollectionCredentialResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_collection_credential(request: Request, order_id: int, payload: CollectionCredentialIssueRequest, x_guest_access_token: str | None = Header(default=None), db: Session = Depends(get_db), user: User | None = Depends(get_optional_current_user)):
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    _authorize_customer_order(order, user, x_guest_access_token)
    try:
        return issue_collection_credential(db, order, rotate=payload.rotate)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.post("/branches/{branch_id}/collection/redeem")
@limiter.limit("10/minute")
def redeem_collection(request: Request, branch_id: uuid.UUID, payload: CollectionRedemptionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found.")
    _authorize_collection_branch(db, user, branch)
    try:
        return redeem_collection_credential(
            db, branch_id=branch_id, raw_credential=payload.credential,
            credential_type=payload.credential_type, staff_user_id=user.id,
            handoff_name=payload.handoff_name, handoff_phone=payload.handoff_phone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
