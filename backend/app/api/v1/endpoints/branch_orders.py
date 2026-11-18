"""Unified public branch order endpoint for preorder and onsite QR."""
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from app.api.deps import get_db
from app.core.security import decode_token
from app.services.auth_service import get_user_by_id
from app.models.user import User, UserRole
from app.schemas.branch_order import BranchOrderCreate
from app.services.branch_order_service import create_branch_order
from app.core.config import get_settings
from app.core.rate_limiter import limiter

router = APIRouter(prefix="/orders", tags=["orders"])
settings = get_settings()

@router.post("/branch", status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_ORDER_CREATE)
def create_branch_order_endpoint(request: Request, payload: BranchOrderCreate, authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user = None
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Invalid authorization header.")
        try: claims = decode_token(token)
        except ValueError as exc: raise HTTPException(status_code=401, detail="Invalid access token.") from exc
        if claims.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid access token.")
        try: user_id = uuid.UUID(str(claims.get("sub")))
        except (ValueError, TypeError) as exc: raise HTTPException(status_code=401, detail="Invalid access token.") from exc
        user = get_user_by_id(db, user_id)
        if user is None or not user.is_active: raise HTTPException(status_code=401, detail="Invalid access token.")
        if user.role not in (UserRole.CUSTOMER, UserRole.ADMIN): raise HTTPException(status_code=403, detail="Customer account required.")
    try:
        order, guest_token = create_branch_order(db, payload, user.id if user else None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": order.id, "branch_id": order.branch_id, "order_source": order.order_source,
        "fulfillment_method": order.fulfillment_method, "total_amount": order.total_amount,
        "status": order.status.value, "payment_reference": order.payment_reference,
        "guest_access_token": guest_token,
    }
