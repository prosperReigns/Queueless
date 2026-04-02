"""User-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Request payload for creating a user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.CUSTOMER

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("Password cannot start or end with whitespace.")
        if value.isspace():
            raise ValueError("Password cannot be only whitespace.")
        return value


class UserUpdate(BaseModel):
    """Request payload for updating mutable user fields."""

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class UserResponse(BaseModel):
    """Response payload for a user."""

    id: uuid.UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
