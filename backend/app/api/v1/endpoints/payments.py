"""Payment endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.user import User, UserRole
from app.schemas.payment import PaymentInitiateRequest, PaymentInitiateResponse
from app.services.payment_service import (
    handle_paystack_webhook_event,
    initialize_paystack_payment,
    verify_paystack_webhook_signature,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/initiate", response_model=PaymentInitiateResponse)
def initiate_payment(
    payload: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CUSTOMER)),
) -> PaymentInitiateResponse:
    """Initialize a Paystack transaction for an order."""
    try:
        result = initialize_paystack_payment(
            db,
            order_id=payload.order_id,
            user=current_user,
            callback_url=payload.callback_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return PaymentInitiateResponse(
        payment=result["payment"],
        authorization_url=result["authorization_url"],
        access_code=result["access_code"],
        reference=result["reference"],
    )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Handle Paystack webhook with signature verification and idempotency."""
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")
    if not verify_paystack_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature.")

    processed = handle_paystack_webhook_event(db, raw_body)
    if not processed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook event not processed.")
    return {"status": "ok"}
