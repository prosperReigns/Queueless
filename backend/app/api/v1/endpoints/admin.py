"""Admin endpoints."""

from __future__ import annotations

from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.user import User, UserRole
from app.schemas.store import StoreResponse
from app.schemas.user import UserResponse
from app.services.auth_service import get_user_by_id, list_users, set_user_active_status
from app.services.cache_service import cache_service
from app.services.store_service import get_store_by_id, list_stores, set_store_active_status

router = APIRouter(prefix="/admin", tags=["admin"])


class ActiveStatusUpdate(BaseModel):
    """Payload for toggling active/inactive state."""

    is_active: bool


@router.get("/users", response_model=List[UserResponse])
def list_users_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> List[UserResponse]:
    """List all users (admin only)."""
    users = list_users(db)
    return [UserResponse.model_validate(user) for user in users]


@router.patch("/users/{user_id}/active", response_model=UserResponse)
def set_user_active_endpoint(
    user_id: uuid.UUID,
    payload: ActiveStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> UserResponse:
    """Activate or deactivate a user account (admin only)."""
    target_user = get_user_by_id(db, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if target_user.id == current_user.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot deactivate own account.",
        )
    updated = set_user_active_status(db, target_user, payload.is_active)
    return UserResponse.model_validate(updated)


@router.get("/stores", response_model=List[StoreResponse])
def list_stores_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> List[StoreResponse]:
    """List all stores (admin only)."""
    stores = list_stores(db)
    return [StoreResponse.model_validate(store) for store in stores]


@router.patch("/stores/{store_id}/active", response_model=StoreResponse)
def set_store_active_endpoint(
    store_id: int,
    payload: ActiveStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> StoreResponse:
    """Activate or deactivate a store (admin only)."""
    target_store = get_store_by_id(db, store_id)
    if target_store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    updated = set_store_active_status(db, target_store, payload.is_active)
    cache_service.invalidate_store_list()
    cache_service.invalidate_store_products(store_id)
    return StoreResponse.model_validate(updated)
