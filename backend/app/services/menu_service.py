"""Business menu and branch override services."""
from __future__ import annotations
import uuid
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.business import Business
from app.models.branch import Branch
from app.models.menu import MenuCategory, MenuItem, BranchMenuItem

def create_category(db: Session, business: Business, payload) -> MenuCategory:
    row = MenuCategory(business_id=business.id, name=payload.name.strip(), description=payload.description, sort_order=payload.sort_order)
    db.add(row); db.commit(); db.refresh(row); return row

def create_menu_item(db: Session, business: Business, payload) -> MenuItem:
    if payload.category_id:
        category = db.get(MenuCategory, payload.category_id)
        if category is None or category.business_id != business.id:
            raise ValueError("Category does not belong to this business.")
    row = MenuItem(business_id=business.id, category_id=payload.category_id, name=payload.name.strip(), description=payload.description, base_price=payload.base_price, image_url=str(payload.image_url) if payload.image_url else None)
    db.add(row); db.commit(); db.refresh(row); return row

def set_branch_item(db: Session, branch: Branch, item_id: uuid.UUID, payload) -> BranchMenuItem:
    item = db.get(MenuItem, item_id)
    if item is None or item.business_id != branch.business_id:
        raise ValueError("Menu item does not belong to this branch's business.")
    row = db.scalar(select(BranchMenuItem).where(BranchMenuItem.branch_id == branch.id, BranchMenuItem.menu_item_id == item_id))
    if row is None:
        row = BranchMenuItem(branch_id=branch.id, menu_item_id=item_id)
        db.add(row)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit(); db.refresh(row); return row

def get_public_branch_menu(db: Session, branch: Branch):
    stmt = (select(MenuCategory, MenuItem, BranchMenuItem)
        .join(MenuItem, MenuItem.category_id == MenuCategory.id, isouter=True)
        .join(BranchMenuItem, (BranchMenuItem.menu_item_id == MenuItem.id) & (BranchMenuItem.branch_id == branch.id), isouter=True)
        .where(MenuCategory.business_id == branch.business_id, MenuCategory.is_active.is_(True), MenuItem.is_active.is_(True))
        .order_by(MenuCategory.sort_order, MenuItem.name))
    rows = db.execute(stmt).all()
    grouped = {}
    for category, item, override in rows:
        grouped.setdefault(category.id, {"id": category.id, "name": category.name, "description": category.description, "sort_order": category.sort_order, "items": []})
        if item is None or (override is not None and not override.is_available):
            continue
        grouped[category.id]["items"].append({
            "id": item.id, "category_id": item.category_id, "name": item.name,
            "description": item.description,
            "price": override.price_override if override and override.price_override is not None else item.base_price,
            "image_url": item.image_url,
            "is_available": True,
        })
    return list(grouped.values())
