"""Payment-related Pydantic schemas."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.payment import PaymentProvider, PaymentStatus

class PaymentInitiateRequest(BaseModel):
    order_id: int = Field(gt=0)
    callback_url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    guest_access_token: Optional[str] = Field(default=None, min_length=32, max_length=128)

class PaymentWebhookRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=255)
    status: PaymentStatus
    amount: Decimal = Field(gt=Decimal("0"), max_digits=10, decimal_places=2)
    provider: PaymentProvider = PaymentProvider.PAYSTACK

class PaymentResponse(BaseModel):
    id: int = Field(gt=0)
    order_id: int = Field(gt=0)
    reference: str = Field(min_length=1, max_length=255)
    status: PaymentStatus
    amount: Decimal = Field(gt=Decimal("0"), max_digits=10, decimal_places=2)
    provider: PaymentProvider
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PaymentInitiateResponse(BaseModel):
    payment: PaymentResponse
    authorization_url: str = Field(min_length=1, max_length=2048)
    access_code: str = Field(min_length=1, max_length=255)
    reference: str = Field(min_length=1, max_length=255)
