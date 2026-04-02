"""Order item-related Pydantic schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    """Request payload for creating an order item."""

    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderItemResponse(BaseModel):
    """Response payload for an order item."""

    id: int = Field(gt=0)
    order_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    price: Decimal = Field(gt=Decimal("0"), max_digits=10, decimal_places=2)

    model_config = ConfigDict(from_attributes=True)
