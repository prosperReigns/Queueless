"""QR code-related Pydantic schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.order import OrderStatus


class QRCodeResponse(BaseModel):
    """Response payload for generated order QR code."""

    order_id: int = Field(gt=0)
    qr_data: str = Field(min_length=1)
    qr_image_base64: str = Field(min_length=1)
    mime_type: str = Field(default="image/png", min_length=1, max_length=255)


class QRCodeValidationRequest(BaseModel):
    """Request payload for validating scanned QR content."""

    qr_data: str = Field(min_length=1, max_length=8192)


class QRCodeValidationResponse(BaseModel):
    """Response payload for scanned QR validation."""

    is_valid: bool
    message: str = Field(min_length=1, max_length=255)
    order_id: int | None = Field(default=None, gt=0)
    store_id: int | None = Field(default=None, gt=0)
    customer_id: uuid.UUID | None = None
    order_status: OrderStatus | None = None
    pickup_ready: bool | None = None
