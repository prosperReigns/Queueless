"""Authentication token-related Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request payload for logging in."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenPair(BaseModel):
    """Access and refresh token response."""

    access_token: str = Field(min_length=1)
    refresh_token: str = Field(min_length=1)
    token_type: str = Field(default="bearer", min_length=1)


class RefreshTokenRequest(BaseModel):
    """Request payload for token refresh."""

    refresh_token: str = Field(min_length=1)


class AccessTokenResponse(BaseModel):
    """Access token response payload."""

    access_token: str = Field(min_length=1)
    token_type: str = Field(default="bearer", min_length=1)
