"""Product service logic."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def list_products_by_store(db: Session, store_id: int) -> List[Product]:
    """Return products for a store ordered by newest first."""
    stmt = (
        select(Product)
        .where(Product.store_id == store_id)
        .order_by(Product.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    """Return a product by id."""
    return db.get(Product, product_id)


def create_product(db: Session, payload: ProductCreate) -> Product:
    """Create a product for a store."""
    product = Product(
        store_id=payload.store_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        is_available=payload.is_available,
        image_url=str(payload.image_url) if payload.image_url else None,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, payload: ProductUpdate) -> Product:
    """Update mutable fields on a product."""
    updates = payload.model_dump(exclude_unset=True)
    if "image_url" in updates and updates["image_url"] is not None:
        updates["image_url"] = str(updates["image_url"])
    for field, value in updates.items():
        setattr(product, field, value)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product) -> None:
    """Delete a product."""
    db.delete(product)
    db.commit()
