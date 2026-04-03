"""Payment endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.config import get_settings
from app.core.rate_limiter import limiter
from app.models.user import User, UserRole
from app.schemas.payment import PaymentInitiateRequest, PaymentInitiateResponse
from app.services.payment_service import (
    handle_paystack_webhook_event,
    initialize_paystack_payment,
    verify_paystack_webhook_signature,
)

router = APIRouter(prefix="/payments", tags=["payments"])
settings = get_settings()


@router.post("/initiate", response_model=PaymentInitiateResponse)
@limiter.limit(settings.RATE_LIMIT_PAYMENTS)
def initiate_payment(
    request: Request,
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
@limiter.limit(settings.RATE_LIMIT_PAYMENTS)
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Handle Paystack webhook with signature verification and idempotency."""
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")
    if not verify_paystack_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature.")

    processed, reason = handle_paystack_webhook_event(db, raw_body)
    if not processed and reason == "invalid_payload":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook event not processed: {reason}.",
        )
    return {"status": "ok", "processed": str(processed).lower(), "reason": reason}
