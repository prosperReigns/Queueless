"""Business, branch and membership domain services."""
from __future__ import annotations
import re
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.business import Business, BusinessType
from app.models.branch import Branch
from app.models.business_membership import BusinessMembership, BusinessRole
from app.models.branch_qr_code import BranchQRCode
from app.models.user import User
from app.schemas.business import BusinessCreate, BusinessUpdate, BranchCreate, BranchUpdate

def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "restaurant")[:88]

def _unique_business_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    candidate = base
    while db.scalar(select(Business.id).where(Business.slug == candidate)) is not None:
        candidate = f"{base[:88]}-{uuid.uuid4().hex[:6]}"
    return candidate

def _unique_branch_slug(db: Session, business_id: uuid.UUID, name: str) -> str:
    base = _slugify(name)
    candidate = base
    while db.scalar(select(Branch.id).where(Branch.business_id == business_id, Branch.slug == candidate)) is not None:
        candidate = f"{base[:88]}-{uuid.uuid4().hex[:6]}"
    return candidate

def create_business(db: Session, payload: BusinessCreate, owner: User) -> Business:
    business = Business(
        name=payload.name.strip(), slug=_unique_business_slug(db, payload.name),
        business_type=payload.business_type, description=payload.description,
        email=payload.email, phone=payload.phone,
    )
    db.add(business)
    db.flush()
    db.add(BusinessMembership(user_id=owner.id, business_id=business.id, role=BusinessRole.OWNER))
    db.commit()
    db.refresh(business)
    return business

def list_user_businesses(db: Session, user: User) -> list[tuple[Business, Optional[BusinessRole]]]:
    if user.role.value == "admin":
        return [(business, None) for business in db.scalars(select(Business).order_by(Business.created_at.desc())).all()]
    rows = db.execute(
        select(Business, BusinessMembership.role)
        .join(BusinessMembership, BusinessMembership.business_id == Business.id)
        .where(BusinessMembership.user_id == user.id, BusinessMembership.is_active.is_(True), Business.is_active.is_(True))
        .order_by(Business.created_at.desc())
    ).all()
    return [(row[0], row[1]) for row in rows]

def get_business(db: Session, business_id: uuid.UUID) -> Optional[Business]:
    return db.get(Business, business_id)

def update_business(db: Session, business: Business, payload: BusinessUpdate) -> Business:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(business, field, value)
    db.add(business)
    db.commit()
    db.refresh(business)
    return business

def get_membership(db: Session, user_id: uuid.UUID, business_id: uuid.UUID, branch_id: Optional[uuid.UUID] = None) -> Optional[BusinessMembership]:
    stmt = select(BusinessMembership).where(
        BusinessMembership.user_id == user_id,
        BusinessMembership.business_id == business_id,
        BusinessMembership.is_active.is_(True),
    )
    if branch_id is not None:
        stmt = stmt.where((BusinessMembership.branch_id == branch_id) | (BusinessMembership.branch_id.is_(None)))
        return db.scalar(stmt.order_by(BusinessMembership.branch_id.asc().nulls_first()))
    stmt = stmt.where(BusinessMembership.branch_id.is_(None))
    return db.scalar(stmt)

def can_access_business(db: Session, user: User, business_id: uuid.UUID) -> bool:
    if user.role.value == "admin":
        return True
    return get_membership(db, user.id, business_id) is not None

def can_access_branch(db: Session, user: User, branch: Branch) -> bool:
    if user.role.value == "admin":
        return True
    return get_membership(db, user.id, branch.business_id, branch.id) is not None

def create_branch(db: Session, business: Business, payload: BranchCreate) -> Branch:
    branch = Branch(
        business_id=business.id, name=payload.name.strip(),
        slug=_unique_branch_slug(db, business.id, payload.name),
        address_line=payload.address_line, city=payload.city, state=payload.state,
        country=payload.country.upper(), phone=payload.phone, timezone=payload.timezone,
        notes=payload.notes,
    )
    branch.qr_code = BranchQRCode(token=uuid.uuid4())
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch

def list_branches(db: Session, business_id: uuid.UUID) -> list[Branch]:
    return list(db.scalars(select(Branch).where(Branch.business_id == business_id).order_by(Branch.created_at.asc())).all())

def get_branch(db: Session, branch_id: uuid.UUID) -> Optional[Branch]:
    return db.get(Branch, branch_id)

def update_branch(db: Session, branch: Branch, payload: BranchUpdate) -> Branch:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(branch, field, value.upper() if field == "country" and value else value)
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch

def create_membership(db: Session, business: Business, payload, actor_role: BusinessRole) -> BusinessMembership:
    if payload.role == BusinessRole.OWNER:
        raise ValueError("Owner membership cannot be assigned through staff management.")
    if payload.role == BusinessRole.FRANCHISE_ADMIN:
        if business.business_type != BusinessType.FRANCHISE or actor_role != BusinessRole.OWNER:
            raise PermissionError("Only the business owner can appoint a franchise administrator.")
        if payload.branch_id is not None:
            raise ValueError("Franchise administrators must be assigned at business scope.")
    else:
        if payload.branch_id is None:
            raise ValueError("Branch staff roles require a branch_id.")
        branch = db.get(Branch, payload.branch_id)
        if branch is None or branch.business_id != business.id:
            raise ValueError("The selected branch does not belong to this business.")
    duplicate_stmt = select(BusinessMembership.id).where(
        BusinessMembership.user_id == payload.user_id,
        BusinessMembership.business_id == business.id,
        BusinessMembership.branch_id == payload.branch_id,
        BusinessMembership.is_active.is_(True),
    )
    if db.scalar(duplicate_stmt) is not None:
        raise ValueError("This user already has an active membership at the selected scope.")
    membership = BusinessMembership(user_id=payload.user_id, business_id=business.id, branch_id=payload.branch_id, role=payload.role)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership
