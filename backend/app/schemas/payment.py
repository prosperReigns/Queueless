"""Payment API request and response schemas."""
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

class PaymentVerifyRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=255)
    guest_access_token: Optional[str] = Field(default=None, min_length=32, max_length=128)

class PaymentRefundRequest(BaseModel):
    payment_reference: str = Field(min_length=1, max_length=255)
    amount: Optional[Decimal] = Field(default=None, gt=Decimal("0"), max_digits=10, decimal_places=2)
    reason: Optional[str] = Field(default=None, max_length=500)

class PaymentResponse(BaseModel):
    id: int
    order_id: int
    reference: str
    status: PaymentStatus
    amount: Decimal
    currency: str = "NGN"
    provider: PaymentProvider
    provider_transaction_id: Optional[str] = None
    amount_refunded: Decimal = Decimal("0.00")
    paid_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class PaymentInitiateResponse(BaseModel):
    payment: PaymentResponse
    authorization_url: str
    access_code: str
    reference: str

class PaymentRefundResponse(BaseModel):
    id: int
    payment_id: int
    reference: str
    provider_refund_id: Optional[str] = None
    amount: Decimal
    currency: str
    status: str
    reason: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
