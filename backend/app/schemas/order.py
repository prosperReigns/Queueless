"""Order-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus
from app.schemas.order_item import OrderItemCreate, OrderItemResponse


class OrderCreate(BaseModel):
    """Request payload for creating an order."""

    store_id: int = Field(gt=0)
    items: List[OrderItemCreate] = Field(min_length=1)


class OrderStatusUpdate(BaseModel):
    """Request payload for updating an order status."""

    status: OrderStatus


class OrderResponse(BaseModel):
    """Response payload for an order."""

    id: int = Field(gt=0)
    user_id: Optional[uuid.UUID] = None
    store_id: Optional[int] = Field(default=None, gt=0)
    branch_id: Optional[uuid.UUID] = None
    order_source: Optional[str] = None
    fulfillment_method: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    total_amount: Decimal = Field(ge=Decimal("0"), max_digits=10, decimal_places=2)
    status: OrderStatus
    payment_reference: str = Field(min_length=1, max_length=255)
    created_at: datetime
    items: List[OrderItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
