"""Product-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProductBase(BaseModel):
    """Shared product fields."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    price: Decimal = Field(ge=Decimal("0"), max_digits=10, decimal_places=2)
    is_available: bool = True
    image_url: HttpUrl | None = None


class ProductCreate(ProductBase):
    """Request payload for creating a product."""

    store_id: int = Field(gt=0)


class ProductUpdate(BaseModel):
    """Request payload for updating a product."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    price: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=10, decimal_places=2)
    is_available: bool | None = None
    image_url: HttpUrl | None = None

    model_config = ConfigDict(extra="forbid")


class ProductResponse(ProductBase):
    """Response payload for a product."""

    id: int = Field(gt=0)
    store_id: int = Field(gt=0)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
