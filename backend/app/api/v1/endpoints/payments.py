"""Payment endpoints for Paystack initialization, verification and refunds."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import secrets
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_optional_current_user, get_current_active_user
from app.core.config import get_settings
from app.core.rate_limiter import limiter
from app.models.business_membership import BusinessMembership, BusinessRole
from app.models.branch import Branch
from app.models.order import Order
from app.models.payment import Payment
from app.models.store import Store
from app.models.user import User, UserRole
from app.schemas.payment import (
    PaymentInitiateRequest, PaymentInitiateResponse, PaymentVerifyRequest,
    PaymentRefundRequest, PaymentRefundResponse,
)
from app.services.payment_service import (
    handle_paystack_webhook_event, initialize_paystack_payment,
    initiate_paystack_refund, verify_paystack_webhook_signature,
    verify_payment_and_reconcile,
)

router = APIRouter(prefix="/payments", tags=["payments"])
settings = get_settings()

@router.post("/initiate", response_model=PaymentInitiateResponse)
@limiter.limit(settings.RATE_LIMIT_PAYMENTS)
def initiate_payment(
    request: Request, payload: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> PaymentInitiateResponse:
    try:
        result = initialize_paystack_payment(
            db, order_id=payload.order_id, user=current_user,
            guest_access_token=payload.guest_access_token,
            callback_url=payload.callback_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PaymentInitiateResponse(
        payment=result["payment"], authorization_url=result["authorization_url"],
        access_code=result["access_code"], reference=result["reference"],
    )

@router.post("/verify")
@limiter.limit(settings.RATE_LIMIT_PAYMENTS)
def verify_payment(
    request: Request, payload: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    payment = db.scalar(select(Payment).where(Payment.reference == payload.reference))
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found.")
    order = db.get(Order, payment.order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    if current_user is not None:
        if current_user.role != UserRole.ADMIN and order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Payment access denied.")
    else:
        supplied_hash = hashlib.sha256((payload.guest_access_token or "").encode()).hexdigest()
        if (order.user_id is not None or not order.guest_access_token_hash
            or not order.guest_access_token_expires_at
            or order.guest_access_token_expires_at <= datetime.now(timezone.utc)
            or not secrets.compare_digest(supplied_hash, order.guest_access_token_hash)):
            raise HTTPException(status_code=401, detail="Valid guest checkout token required.")
    try:
        verified_payment, provider_status = verify_payment_and_reconcile(db, payload.reference)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"payment": verified_payment, "provider_status": provider_status, "order_status": order.status.value}

def _authorize_refund(db: Session, user: User, payment: Payment) -> None:
    if user.role == UserRole.ADMIN:
        return
    order = db.get(Order, payment.order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.branch_id is not None:
        membership = db.scalar(select(BusinessMembership.id).where(
            BusinessMembership.user_id == user.id,
            BusinessMembership.business_id == db.get(Branch, order.branch_id).business_id,
            BusinessMembership.is_active.is_(True),
            BusinessMembership.role.in_([BusinessRole.OWNER, BusinessRole.FRANCHISE_ADMIN, BusinessRole.BRANCH_MANAGER]),
            (BusinessMembership.branch_id.is_(None)) | (BusinessMembership.branch_id == order.branch_id),
        ))
        if membership:
            return
    elif order.store_id is not None and user.role == UserRole.MERCHANT:
        store = db.get(Store, order.store_id)
        if store is not None and store.owner_id == user.id:
            return
    raise HTTPException(status_code=403, detail="You are not allowed to refund this payment.")

@router.post("/refunds", response_model=PaymentRefundResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_PAYMENTS)
def create_refund(
    request: Request, payload: PaymentRefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaymentRefundResponse:
    payment = db.scalar(select(Payment).where(Payment.reference == payload.payment_reference))
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found.")
    _authorize_refund(db, current_user, payment)
    try:
        refund = initiate_paystack_refund(
            db, payment_reference=payload.payment_reference,
            amount=payload.amount, reason=payload.reason,
            initiated_by=str(current_user.id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PaymentRefundResponse.model_validate(refund)

@router.post("/webhook", status_code=status.HTTP_200_OK)
@limiter.limit(settings.RATE_LIMIT_PAYMENT_WEBHOOK)
async def paystack_webhook(request: Request, db: Session = Depends(get_db)) -> Dict[str, str]:
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")
    if not verify_paystack_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature.")
    processed, reason = handle_paystack_webhook_event(db, raw_body)
    if reason == "invalid_payload":
        raise HTTPException(status_code=400, detail="Invalid webhook payload.")
    if reason == "verification_unavailable":
        raise HTTPException(status_code=503, detail="Payment verification is temporarily unavailable; retry webhook.")
    return {"status": "ok", "processed": str(processed).lower(), "reason": reason}
