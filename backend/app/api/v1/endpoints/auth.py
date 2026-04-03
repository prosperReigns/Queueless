"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.config import get_settings
from app.core.rate_limiter import limiter
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
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """Register a new user account."""
    try:
        user = register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenPair)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
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
@limiter.limit(settings.RATE_LIMIT_AUTH)
def refresh_access_token(
    request: Request,
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
