"""Store-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class StoreBase(BaseModel):
    """Shared store fields."""

    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    location: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = True


class StoreCreate(StoreBase):
    """Request payload for creating a store."""

    pass


class StoreUpdate(BaseModel):
    """Request payload for updating a store."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    location: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class StoreResponse(StoreBase):
    """Response payload for a store."""

    id: int = Field(gt=0)
    owner_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
