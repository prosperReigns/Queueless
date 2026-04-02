"""QR code endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User, UserRole
from app.schemas.qr_code import (
    QRCodeResponse,
    QRCodeValidationRequest,
    QRCodeValidationResponse,
)
from app.services.order_service import get_order_by_id
from app.services.qr_code_service import (
    generate_order_qr_image_base64,
    get_order_qr_data,
    is_order_pickup_ready,
    validate_scanned_qr_data,
)
from app.services.store_service import get_store_by_id

router = APIRouter(prefix="/qr-codes", tags=["qr-codes"])


def _authorize_order_access(db: Session, current_user: User, order_user_id: object, order_store_id: int) -> None:
    """Authorize access to a specific order for customer/merchant roles."""
    if current_user.role == UserRole.CUSTOMER and order_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions.")
    if current_user.role == UserRole.MERCHANT:
        store = get_store_by_id(db, order_store_id)
        if store is None or store.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions.")


@router.get("/orders/{order_id}", response_model=QRCodeResponse)
def generate_order_qr_code(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> QRCodeResponse:
    """Generate QR code payload/image for an order visible to the caller."""
    order = get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    _authorize_order_access(db, current_user, order.user_id, order.store_id)

    qr_data = get_order_qr_data(order)
    qr_image_base64 = generate_order_qr_image_base64(order)
    return QRCodeResponse(order_id=order.id, qr_data=qr_data, qr_image_base64=qr_image_base64)


@router.post("/validate", response_model=QRCodeValidationResponse)
def validate_scanned_qr_code(
    payload: QRCodeValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> QRCodeValidationResponse:
    """Validate scanned order QR content and return order context."""
    is_valid, message, order = validate_scanned_qr_data(db, payload.qr_data)
    if not is_valid or order is None:
        return QRCodeValidationResponse(is_valid=False, message=message)

    _authorize_order_access(db, current_user, order.user_id, order.store_id)

    return QRCodeValidationResponse(
        is_valid=True,
        message=message,
        order_id=order.id,
        store_id=order.store_id,
        customer_id=order.user_id,
        order_status=order.status,
        pickup_ready=is_order_pickup_ready(order),
    )
