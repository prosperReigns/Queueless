"""Store service logic."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.store import Store
from app.schemas.store import StoreCreate, StoreUpdate


def list_stores(db: Session) -> list[Store]:
    """Return all stores ordered by newest first."""
    stmt = select(Store).order_by(Store.created_at.desc())
    return list(db.scalars(stmt).all())


def get_store_by_id(db: Session, store_id: int) -> Store | None:
    """Return a store by id."""
    return db.get(Store, store_id)


def create_store(db: Session, payload: StoreCreate, owner_id: uuid.UUID) -> Store:
    """Create a merchant-owned store."""
    store = Store(
        name=payload.name,
        description=payload.description,
        owner_id=owner_id,
        location=payload.location,
        is_active=payload.is_active,
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


def update_store(db: Session, store: Store, payload: StoreUpdate) -> Store:
    """Update mutable fields on a store."""
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(store, field, value)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


def delete_store(db: Session, store: Store) -> None:
    """Delete a store."""
    db.delete(store)
    db.commit()
