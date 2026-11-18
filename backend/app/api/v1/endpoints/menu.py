"""Branch-aware menu endpoints."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_user
from app.models.user import User, UserRole
from app.models.branch import Branch
from app.models.business import Business
from app.models.business_membership import BusinessRole, BusinessMembership
from app.models.branch_qr_code import BranchQRCode
from app.services.business_service import can_access_branch
from app.services.menu_service import create_category, create_menu_item, get_public_branch_menu, set_branch_item
from app.schemas.menu import MenuCategoryCreate, MenuItemCreate, BranchMenuItemUpdate

router = APIRouter(tags=["menus"])

def _manager_access(db: Session, user: User, branch: Branch) -> None:
    if user.role == UserRole.ADMIN:
        return
    if not can_access_branch(db, user, branch):
        raise HTTPException(status_code=403, detail="Branch access denied.")
    allowed = db.scalar(select(BusinessMembership.id).where(
        BusinessMembership.user_id == user.id,
        BusinessMembership.business_id == branch.business_id,
        BusinessMembership.is_active.is_(True),
        BusinessMembership.role.in_([BusinessRole.OWNER, BusinessRole.FRANCHISE_ADMIN, BusinessRole.BRANCH_MANAGER]),
        (BusinessMembership.branch_id == branch.id) | (BusinessMembership.branch_id.is_(None)),
    ))
    if not allowed:
        raise HTTPException(status_code=403, detail="Menu management permission required.")

def _public_menu_payload(db: Session, branch: Branch):
    return {
        "business": {"id": str(branch.business.id), "name": branch.business.name, "slug": branch.business.slug},
        "branch": {"id": str(branch.id), "name": branch.name, "timezone": branch.timezone, "address_line": branch.address_line, "city": branch.city, "state": branch.state, "country": branch.country},
        "categories": get_public_branch_menu(db, branch),
    }

@router.get("/public/businesses/{business_slug}/branches")
def public_business_branches(business_slug: str, db: Session = Depends(get_db)):
    business = db.scalar(select(Business).where(Business.slug == business_slug, Business.is_active.is_(True)))
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found.")
    branches = db.scalars(select(Branch).where(Branch.business_id == business.id, Branch.is_active.is_(True)).order_by(Branch.name)).all()
    return [{"id": branch.id, "name": branch.name, "address_line": branch.address_line, "city": branch.city, "state": branch.state, "country": branch.country, "timezone": branch.timezone} for branch in branches]

@router.get("/public/branches/{branch_id}/menu")
def public_branch_menu_by_id(branch_id: uuid.UUID, db: Session = Depends(get_db)):
    branch = db.get(Branch, branch_id)
    if branch is None or not branch.is_active or not branch.business.is_active:
        raise HTTPException(status_code=404, detail="Branch menu not found.")
    return _public_menu_payload(db, branch)

@router.get("/public/branches/resolve/{token}/menu")
def public_branch_menu(token: uuid.UUID, db: Session = Depends(get_db)):
    qr = db.scalar(select(BranchQRCode).where(BranchQRCode.token == token, BranchQRCode.is_active.is_(True)))
    branch = db.get(Branch, qr.branch_id) if qr else None
    if branch is None or not branch.is_active or not branch.business.is_active:
        raise HTTPException(status_code=404, detail="Branch menu not found.")
    return _public_menu_payload(db, branch)

@router.post("/businesses/{business_id}/menu/categories", status_code=status.HTTP_201_CREATED)
def add_menu_category(business_id: uuid.UUID, payload: MenuCategoryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    business = db.get(Business, business_id)
    if business is None or not business.is_active:
        raise HTTPException(status_code=404, detail="Business not found.")
    allowed = user.role == UserRole.ADMIN or db.scalar(select(BusinessMembership.id).where(
        BusinessMembership.user_id == user.id, BusinessMembership.business_id == business_id,
        BusinessMembership.is_active.is_(True),
        BusinessMembership.role.in_([BusinessRole.OWNER, BusinessRole.FRANCHISE_ADMIN]),
    ))
    if not allowed:
        raise HTTPException(status_code=403, detail="Business menu management permission required.")
    category = create_category(db, business, payload)
    return {"id": category.id, "business_id": category.business_id, "name": category.name, "description": category.description, "sort_order": category.sort_order, "is_active": category.is_active}

@router.post("/businesses/{business_id}/menu/items", status_code=status.HTTP_201_CREATED)
def add_menu_item(business_id: uuid.UUID, payload: MenuItemCreate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    business = db.get(Business, business_id)
    if business is None or not business.is_active:
        raise HTTPException(status_code=404, detail="Business not found.")
    allowed = user.role == UserRole.ADMIN or db.scalar(select(BusinessMembership.id).where(
        BusinessMembership.user_id == user.id, BusinessMembership.business_id == business_id,
        BusinessMembership.is_active.is_(True),
        BusinessMembership.role.in_([BusinessRole.OWNER, BusinessRole.FRANCHISE_ADMIN]),
    ))
    if not allowed:
        raise HTTPException(status_code=403, detail="Business menu management permission required.")
    try:
        item = create_menu_item(db, business, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": item.id, "business_id": item.business_id, "category_id": item.category_id, "name": item.name, "description": item.description, "base_price": item.base_price, "image_url": item.image_url, "is_active": item.is_active}

@router.patch("/branches/{branch_id}/menu/items/{item_id}")
def update_branch_menu_item(branch_id: uuid.UUID, item_id: uuid.UUID, payload: BranchMenuItemUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found.")
    _manager_access(db, user, branch)
    try:
        override = set_branch_item(db, branch, item_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": override.id, "branch_id": override.branch_id, "menu_item_id": override.menu_item_id, "is_available": override.is_available, "price_override": override.price_override}
