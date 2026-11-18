"""Business, branch, staff membership and permanent branch QR endpoints."""
from __future__ import annotations
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.config import get_settings
from app.models.business import Business
from app.models.branch import Branch
from app.models.business_membership import BusinessMembership, BusinessRole
from app.models.branch_qr_code import BranchQRCode
from app.models.user import User, UserRole
from app.schemas.business import (
    BusinessCreate, BusinessResponse, BusinessUpdate, BusinessWithRoleResponse,
    BranchCreate, BranchResponse, BranchUpdate, MembershipCreate, MembershipResponse,
    BranchQRResponse, PublicBranchResolveResponse, MembershipUpdate,
)
from app.services.business_service import (
    can_access_branch, can_access_business, create_branch, create_business,
    create_membership, get_branch, get_business, get_membership, list_branches,
    list_user_businesses, update_branch, update_business,
)

router = APIRouter(tags=["businesses", "branches", "memberships"])


def _require_business_access(db: Session, user: User, business_id: uuid.UUID) -> Business:
    business = get_business(db, business_id)
    if business is None or not can_access_business(db, user, business_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")
    return business


def _require_business_admin(db: Session, user: User, business_id: uuid.UUID) -> tuple[Business, BusinessRole]:
    business = _require_business_access(db, user, business_id)
    if user.role == UserRole.ADMIN:
        return business, BusinessRole.OWNER
    membership = get_membership(db, user.id, business_id)
    if membership is None or membership.branch_id is not None or membership.role not in {
        BusinessRole.OWNER, BusinessRole.FRANCHISE_ADMIN
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business administrator access required.")
    return business, membership.role


@router.post("/businesses", response_model=BusinessResponse, status_code=status.HTTP_201_CREATED)
def create_business_endpoint(
    payload: BusinessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BusinessResponse:
    """Register a business and automatically assign its creator as owner."""
    business = create_business(db, payload, current_user)
    return BusinessResponse.model_validate(business)


@router.get("/businesses", response_model=List[BusinessWithRoleResponse])
def list_businesses_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[BusinessWithRoleResponse]:
    """List businesses the current user administers or works for."""
    return [
        BusinessWithRoleResponse.model_validate({**BusinessResponse.model_validate(business).model_dump(), "membership_role": role})
        for business, role in list_user_businesses(db, current_user)
    ]


@router.get("/businesses/{business_id}", response_model=BusinessWithRoleResponse)
def get_business_endpoint(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BusinessWithRoleResponse:
    business = _require_business_access(db, current_user, business_id)
    membership = None
    if current_user.role != UserRole.ADMIN:
        membership = db.scalar(
            select(BusinessMembership).where(
                BusinessMembership.user_id == current_user.id,
                BusinessMembership.business_id == business_id,
                BusinessMembership.is_active.is_(True),
            ).order_by(BusinessMembership.branch_id.asc().nulls_first())
        )
    response = BusinessResponse.model_validate(business).model_dump()
    response["membership_role"] = membership.role if membership else None
    return BusinessWithRoleResponse.model_validate(response)


@router.patch("/businesses/{business_id}", response_model=BusinessResponse)
def update_business_endpoint(
    business_id: uuid.UUID,
    payload: BusinessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BusinessResponse:
    business, _ = _require_business_admin(db, current_user, business_id)
    return BusinessResponse.model_validate(update_business(db, business, payload))


@router.post("/businesses/{business_id}/branches", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch_endpoint(
    business_id: uuid.UUID,
    payload: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BranchResponse:
    business, _ = _require_business_admin(db, current_user, business_id)
    return BranchResponse.model_validate(create_branch(db, business, payload))


@router.get("/businesses/{business_id}/branches", response_model=List[BranchResponse])
def list_business_branches_endpoint(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[BranchResponse]:
    _require_business_access(db, current_user, business_id)
    branches = list_branches(db, business_id)
    if current_user.role == UserRole.ADMIN:
        return [BranchResponse.model_validate(branch) for branch in branches]
    membership = get_membership(db, current_user.id, business_id)
    if membership is not None:
        return [BranchResponse.model_validate(branch) for branch in branches]
    assigned_branch_ids = set(db.scalars(
        select(BusinessMembership.branch_id).where(
            BusinessMembership.user_id == current_user.id,
            BusinessMembership.business_id == business_id,
            BusinessMembership.is_active.is_(True),
            BusinessMembership.branch_id.is_not(None),
        )
    ).all())
    return [BranchResponse.model_validate(branch) for branch in branches if branch.id in assigned_branch_ids]


@router.get("/branches/{branch_id}", response_model=BranchResponse)
def get_branch_endpoint(
    branch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BranchResponse:
    branch = get_branch(db, branch_id)
    if branch is None or not can_access_branch(db, current_user, branch):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found.")
    return BranchResponse.model_validate(branch)


@router.patch("/branches/{branch_id}", response_model=BranchResponse)
def update_branch_endpoint(
    branch_id: uuid.UUID,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BranchResponse:
    branch = get_branch(db, branch_id)
    if branch is None or not can_access_branch(db, current_user, branch):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found.")
    if current_user.role != UserRole.ADMIN:
        membership = get_membership(db, current_user.id, branch.business_id, branch.id)
        if membership is None or membership.role not in {
            BusinessRole.OWNER, BusinessRole.FRANCHISE_ADMIN, BusinessRole.BRANCH_MANAGER
        }:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch management access required.")
    return BranchResponse.model_validate(update_branch(db, branch, payload))


@router.post("/businesses/{business_id}/memberships", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
def create_membership_endpoint(
    business_id: uuid.UUID,
    payload: MembershipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MembershipResponse:
    business, actor_role = _require_business_admin(db, current_user, business_id)
    if current_user.role == UserRole.ADMIN:
        actor_role = BusinessRole.OWNER
    target_user = db.get(User, payload.user_id)
    if target_user is None or not target_user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active user not found.")
    try:
        membership = create_membership(db, business, payload, actor_role)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return MembershipResponse.model_validate(membership)


@router.get("/businesses/{business_id}/memberships", response_model=List[MembershipResponse])
def list_memberships_endpoint(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[MembershipResponse]:
    _require_business_admin(db, current_user, business_id)
    memberships = db.scalars(
        select(BusinessMembership).where(BusinessMembership.business_id == business_id).order_by(BusinessMembership.created_at.asc())
    ).all()
    return [MembershipResponse.model_validate(item) for item in memberships]


@router.patch("/businesses/{business_id}/memberships/{membership_id}", response_model=MembershipResponse)
def update_membership_endpoint(
    business_id: uuid.UUID,
    membership_id: uuid.UUID,
    payload: MembershipUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MembershipResponse:
    """Activate or suspend a staff membership without deleting its audit history."""
    _, actor_role = _require_business_admin(db, current_user, business_id)
    if current_user.role == UserRole.ADMIN:
        actor_role = BusinessRole.OWNER
    membership = db.scalar(
        select(BusinessMembership).where(
            BusinessMembership.id == membership_id,
            BusinessMembership.business_id == business_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")
    if membership.role == BusinessRole.OWNER:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The owner membership cannot be changed here.")
    if actor_role == BusinessRole.FRANCHISE_ADMIN and membership.role == BusinessRole.FRANCHISE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can manage franchise administrators.")
    membership.is_active = payload.is_active
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return MembershipResponse.model_validate(membership)


@router.get("/branches/{branch_id}/qr", response_model=BranchQRResponse)
def get_branch_qr_endpoint(
    branch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BranchQRResponse:
    branch = get_branch(db, branch_id)
    if branch is None or not can_access_branch(db, current_user, branch):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found.")
    qr = db.scalar(select(BranchQRCode).where(BranchQRCode.branch_id == branch.id, BranchQRCode.is_active.is_(True)))
    if qr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active branch QR code not found.")
    menu_url = f"{get_settings().FRONTEND_ORIGIN.rstrip('/')}/q/{qr.token}"
    return BranchQRResponse(branch_id=branch.id, token=qr.token, menu_url=menu_url)


@router.get("/public/branches/resolve/{token}", response_model=PublicBranchResolveResponse)
def resolve_branch_qr_endpoint(token: uuid.UUID, db: Session = Depends(get_db)) -> PublicBranchResolveResponse:
    """Resolve a permanent branch QR. This endpoint does not authorize order collection."""
    row = db.execute(
        select(Branch, Business.name)
        .join(Business, Business.id == Branch.business_id)
        .join(BranchQRCode, BranchQRCode.branch_id == Branch.id)
        .where(BranchQRCode.token == token, BranchQRCode.is_active.is_(True),
               Branch.is_active.is_(True), Business.is_active.is_(True))
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch QR code not found or inactive.")
    branch, business_name = row
    return PublicBranchResolveResponse(
        business_id=branch.business_id, business_name=business_name, branch_id=branch.id,
        branch_name=branch.name, address_line=branch.address_line, city=branch.city,
        state=branch.state, country=branch.country, timezone=branch.timezone,
    )
