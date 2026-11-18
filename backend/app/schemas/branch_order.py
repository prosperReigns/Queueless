"""Branch-aware order creation schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class OrderSource(str, Enum):
    PREORDER = "preorder"
    ONSITE_QR = "onsite_qr"

class FulfillmentMethod(str, Enum):
    SELF_COLLECTION = "self_collection"
    EXTERNAL_RIDER = "external_rider"

class BranchOrderItemCreate(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = Field(gt=0, le=50)

class BranchOrderCreate(BaseModel):
    branch_qr_token: uuid.UUID
    source: OrderSource
    fulfillment_method: FulfillmentMethod
    scheduled_for: Optional[datetime] = None
    customer_name: str = Field(min_length=1, max_length=160)
    customer_email: EmailStr
    customer_phone: str = Field(min_length=7, max_length=40)
    items: list[BranchOrderItemCreate] = Field(min_length=1, max_length=30)

class BranchOrderResponse(BaseModel):
    id: int
    branch_id: uuid.UUID
    order_source: OrderSource
    fulfillment_method: FulfillmentMethod
    total_amount: Decimal
    status: str
    payment_reference: str
    guest_access_token: Optional[str] = None
