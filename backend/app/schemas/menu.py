"""Menu API schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

class MenuCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None
    sort_order: int = 0

class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    base_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    image_url: Optional[HttpUrl] = None

class BranchMenuItemUpdate(BaseModel):
    is_available: Optional[bool] = None
    price_override: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)

class MenuItemResponse(BaseModel):
    id: uuid.UUID
    category_id: Optional[uuid.UUID]
    name: str
    description: Optional[str]
    price: Decimal
    image_url: Optional[str]
    is_available: bool
    model_config = ConfigDict(from_attributes=True)

class MenuCategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    sort_order: int
    items: list[MenuItemResponse] = Field(default_factory=list)
