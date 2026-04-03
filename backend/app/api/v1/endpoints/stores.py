"""Store endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import RoleScopeAccess, get_db, get_role_scope_access, require_roles
from app.models.user import User
from app.schemas.store import StoreCreate, StoreResponse, StoreUpdate
from app.services.cache_service import cache_service
from app.services.store_service import (
    create_store,
    delete_store,
    get_store_by_id,
    list_stores,
    update_store,
)

router = APIRouter(prefix="/stores", tags=["stores"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[StoreResponse])
def get_stores(db: Session = Depends(get_db)) -> list[StoreResponse]:
    """List stores."""
    response: list[StoreResponse]
    cached = cache_service.get_json(cache_service.store_list_key())
    if cached is not None:
        try:
            response = [StoreResponse.model_validate(store) for store in cached]
            return response
        except ValidationError:
            logger.warning("Invalid store list cache payload. Rebuilding cache.", exc_info=True)
            cache_service.invalidate_store_list()

    stores = list_stores(db)
    response = [StoreResponse.model_validate(store) for store in stores]
    cache_service.set_json(
        cache_service.store_list_key(),
        [store.model_dump(mode="json") for store in response],
    )
    return response


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store_endpoint(
    payload: StoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MERCHANT)),
) -> StoreResponse:
    """Create a store for the authenticated merchant."""
    store = create_store(db, payload, current_user.id)
    return StoreResponse.model_validate(store)


@router.get("/{store_id}", response_model=StoreResponse)
def get_store(store_id: int, db: Session = Depends(get_db)) -> StoreResponse:
    """Get a store by id."""
    store = get_store_by_id(db, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    return StoreResponse.model_validate(store)


@router.put("/{store_id}", response_model=StoreResponse)
def update_store_endpoint(
    store_id: int,
    payload: StoreUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.MERCHANT)),
    role_scope: RoleScopeAccess = Depends(get_role_scope_access),
) -> StoreResponse:
    """Update an owned store."""
    store = get_store_by_id(db, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    role_scope.enforce_merchant_scope(store.owner_id)
    updated = update_store(db, store, payload)
    cache_service.invalidate_store_list()
    cache_service.invalidate_store_products(store_id)
    return StoreResponse.model_validate(updated)


@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_store_endpoint(
    store_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.MERCHANT)),
    role_scope: RoleScopeAccess = Depends(get_role_scope_access),
) -> Response:
    """Delete an owned store."""
    store = get_store_by_id(db, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    role_scope.enforce_merchant_scope(store.owner_id)
    delete_store(db, store)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
