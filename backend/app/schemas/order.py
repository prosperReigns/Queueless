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
    user_id: uuid.UUID
    store_id: int = Field(gt=0)
    total_amount: Decimal = Field(ge=Decimal("0"), max_digits=10, decimal_places=2)
    status: OrderStatus
    payment_reference: str = Field(min_length=1, max_length=255)
    created_at: datetime
    items: List[OrderItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
