"""Common API dependencies."""

from __future__ import annotations

from collections.abc import Callable
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.services.auth_service import get_user_by_id
from app.db.session import get_db

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Resolve and return the current authenticated user from JWT."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        subject = payload.get("sub")
        token_type = payload.get("type")
        if subject is None or token_type != "access":
            raise credentials_error
        user_id = uuid.UUID(str(subject))
    except (ValueError, TypeError):
        raise credentials_error

    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_error
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user.")
    return current_user


def require_roles(*allowed_roles: UserRole) -> Callable[..., User]:
    """Create dependency that enforces role-based access."""

    def _role_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role == UserRole.ADMIN:
            return current_user
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions.",
            )
        return current_user

    return _role_dependency


__all__ = [
    "get_db",
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_user",
    "require_roles",
]
