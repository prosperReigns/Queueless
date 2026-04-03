"""Notification-related schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationTokenUpsertRequest(BaseModel):
    """Request payload for registering an FCM token."""

    fcm_token: str = Field(min_length=1, max_length=1024)
    device_type: Optional[str] = Field(default=None, max_length=64)

    model_config = ConfigDict(extra="forbid")

    @field_validator("fcm_token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Token cannot be empty.")
        return normalized

    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class NotificationTokenResponse(BaseModel):
    """Response payload for an FCM token."""

    id: int
    user_id: str
    token: str
    device_type: Optional[str]


class NotificationTokenUpsertResponse(BaseModel):
    """Response payload after registering/updating a token."""

    message: str
    token: NotificationTokenResponse
