"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.token import AccessTokenResponse, LoginRequest, RefreshTokenRequest, TokenPair
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import (
    authenticate_user,
    create_access_token_from_refresh_token,
    create_token_pair_for_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """Register a new user account."""
    try:
        user = register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Authenticate user and return JWT tokens."""
    user = authenticate_user(db, payload.email.lower(), payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user.",
        )
    return create_token_pair_for_user(user)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """Return authenticated user profile."""
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_access_token(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> AccessTokenResponse:
    """Refresh access token using a valid refresh token."""
    try:
        access_token = create_access_token_from_refresh_token(db, payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        ) from exc
    return AccessTokenResponse(access_token=access_token)
