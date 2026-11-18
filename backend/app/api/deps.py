"""Common API dependencies."""
from __future__ import annotations
from collections.abc import Callable
import uuid
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.services.auth_service import get_user_by_id
from app.db.session import get_db

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

class RoleScopeAccess:
    def __init__(self, user: User) -> None:
        self.user = user
    def enforce_customer_scope(self, customer_id: uuid.UUID) -> None:
        if self.user.role == UserRole.ADMIN: return
        if self.user.role == UserRole.CUSTOMER and customer_id == self.user.id: return
        raise HTTPException(status_code=403, detail="Not enough permissions.")
    def enforce_merchant_scope(self, merchant_owner_id: uuid.UUID) -> None:
        if self.user.role == UserRole.ADMIN: return
        if self.user.role == UserRole.MERCHANT and merchant_owner_id == self.user.id: return
        raise HTTPException(status_code=403, detail="Not enough permissions.")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_error = HTTPException(status_code=401, detail="Could not validate credentials.", headers={"WWW-Authenticate": "Bearer"})
    try: payload = decode_token(token)
    except ValueError: raise credentials_error
    subject = payload.get("sub")
    if subject is None or payload.get("type") != "access": raise credentials_error
    try: user_id = uuid.UUID(str(subject))
    except (ValueError, TypeError): raise credentials_error
    user = get_user_by_id(db, user_id)
    if user is None: raise credentials_error
    return user

def get_optional_current_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)) -> Optional[User]:
    """Resolve an optional bearer identity for guest-capable checkout/payment routes."""
    if not authorization: return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    try: payload = decode_token(token)
    except ValueError as exc: raise HTTPException(status_code=401, detail="Invalid access token.") from exc
    if payload.get("type") != "access": raise HTTPException(status_code=401, detail="Invalid access token.")
    try: user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError) as exc: raise HTTPException(status_code=401, detail="Invalid access token.") from exc
    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active: raise HTTPException(status_code=401, detail="Invalid access token.")
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active: raise HTTPException(status_code=403, detail="Inactive user.")
    return current_user

def require_roles(*allowed_roles: UserRole) -> Callable[..., User]:
    def _role_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role == UserRole.ADMIN or current_user.role in allowed_roles: return current_user
        raise HTTPException(status_code=403, detail="Not enough permissions.")
    return _role_dependency

def get_role_scope_access(current_user: User = Depends(get_current_active_user)) -> RoleScopeAccess:
    return RoleScopeAccess(current_user)

__all__ = ["get_db", "oauth2_scheme", "get_current_user", "get_current_active_user", "get_optional_current_user", "require_roles", "RoleScopeAccess", "get_role_scope_access"]
