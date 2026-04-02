"""Store-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class StoreBase(BaseModel):
    """Shared store fields."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class StoreCreate(StoreBase):
    """Request payload for creating a store."""

    pass


class StoreUpdate(BaseModel):
    """Request payload for updating a store."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class StoreResponse(StoreBase):
    """Response payload for a store."""

    id: int = Field(gt=0)
    owner_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
