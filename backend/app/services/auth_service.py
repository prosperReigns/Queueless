"""Authentication service logic."""

from __future__ import annotations

from datetime import timedelta
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.token import TokenPair
from app.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by email if present."""
    stmt = select(User).where(User.email == email.lower())
    return db.scalar(stmt)


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """Return a user by id if present."""
    return db.get(User, user_id)


def register_user(db: Session, payload: UserCreate) -> User:
    """Create a new user account."""
    email = payload.email.lower()
    if get_user_by_email(db, email):
        raise ValueError("Email is already registered.")

    user = User(
        email=email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Validate user credentials."""
    user = get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_token_pair_for_user(user: User) -> TokenPair:
    """Generate access and refresh tokens for a user."""
    settings = get_settings()
    access_token = create_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
        extra_claims={"role": user.role.value, "email": user.email},
    )
    refresh_token = create_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES),
        token_type="refresh",
        extra_claims={"role": user.role.value},
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)
