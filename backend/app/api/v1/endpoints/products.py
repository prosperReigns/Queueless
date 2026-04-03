"""Product endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import RoleScopeAccess, get_db, get_role_scope_access, require_roles
from app.models.user import User
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.cache_service import cache_service
from app.services.product_service import (
    create_product,
    delete_product,
    get_product_by_id,
    list_products_by_store,
    update_product,
)
from app.services.store_service import get_store_by_id

router = APIRouter(tags=["products"])
logger = logging.getLogger(__name__)


@router.get("/stores/{store_id}/products", response_model=list[ProductResponse])
def get_store_products(store_id: int, db: Session = Depends(get_db)) -> list[ProductResponse]:
    """List products for a store."""
    response: list[ProductResponse]
    cached = cache_service.get_json(cache_service.store_products_key(store_id))
    if cached is not None:
        try:
            response = [ProductResponse.model_validate(product) for product in cached]
            return response
        except ValidationError:
            logger.warning(
                "Invalid product list cache payload for store_id=%s. Rebuilding cache.",
                store_id,
                exc_info=True,
            )
            cache_service.invalidate_store_products(store_id)

    store = get_store_by_id(db, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    products = list_products_by_store(db, store_id)
    response = [ProductResponse.model_validate(product) for product in products]
    cache_service.set_json(
        cache_service.store_products_key(store_id),
        [product.model_dump(mode="json") for product in response],
    )
    return response


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product_endpoint(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.MERCHANT)),
    role_scope: RoleScopeAccess = Depends(get_role_scope_access),
) -> ProductResponse:
    """Create a product for a merchant-owned store."""
    store = get_store_by_id(db, payload.store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    role_scope.enforce_merchant_scope(store.owner_id)
    product = create_product(db, payload)
    cache_service.invalidate_store_products(payload.store_id)
    return ProductResponse.model_validate(product)


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product_endpoint(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.MERCHANT)),
    role_scope: RoleScopeAccess = Depends(get_role_scope_access),
) -> ProductResponse:
    """Update a product in a merchant-owned store."""
    product = get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    store = get_store_by_id(db, product.store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store associated with this product was not found.",
        )
    role_scope.enforce_merchant_scope(store.owner_id)
    updated = update_product(db, product, payload)
    cache_service.invalidate_store_products(product.store_id)
    return ProductResponse.model_validate(updated)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_product_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.MERCHANT)),
    role_scope: RoleScopeAccess = Depends(get_role_scope_access),
) -> Response:
    """Delete a product in a merchant-owned store."""
    product = get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    store = get_store_by_id(db, product.store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store associated with this product was not found.",
        )
    role_scope.enforce_merchant_scope(store.owner_id)
    delete_product(db, product)
    cache_service.invalidate_store_products(product.store_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
