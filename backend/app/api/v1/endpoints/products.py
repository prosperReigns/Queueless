"""Product endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import RoleScopeAccess, get_db, get_role_scope_access, require_roles
from app.models.user import User
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import (
    create_product,
    delete_product,
    get_product_by_id,
    list_products_by_store,
    update_product,
)
from app.services.store_service import get_store_by_id

router = APIRouter(tags=["products"])


@router.get("/stores/{store_id}/products", response_model=list[ProductResponse])
def get_store_products(store_id: int, db: Session = Depends(get_db)) -> list[ProductResponse]:
    """List products for a store."""
    store = get_store_by_id(db, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    products = list_products_by_store(db, store_id)
    return [ProductResponse.model_validate(product) for product in products]


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
    role_scope.enforce(merchant_owner_id=store.owner_id)
    product = create_product(db, payload)
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
    role_scope.enforce(merchant_owner_id=store.owner_id)
    updated = update_product(db, product, payload)
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
    role_scope.enforce(merchant_owner_id=store.owner_id)
    delete_product(db, product)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
