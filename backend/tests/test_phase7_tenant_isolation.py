"""Additional tenant-isolation regression tests for Phase 7."""

import uuid

from app.models.user import User, UserRole
from app.models.business import BusinessType
from app.models.business_membership import BusinessMembership, BusinessRole
from app.schemas.business import BusinessCreate, BranchCreate, MembershipCreate
from app.services.business_service import (
    can_access_branch,
    can_access_business,
    create_branch,
    create_business,
    create_membership,
)


def _create_user(db, email: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="test-hash",
        role=UserRole.CUSTOMER,
    )
    db.add(user)
    db.commit()
    return user


def test_branch_staff_cannot_cross_business_or_branch_boundary(db_session_fixture):
    db = db_session_fixture
    owner_a = _create_user(db, "phase7-owner-a@example.test")
    owner_b = _create_user(db, "phase7-owner-b@example.test")
    staff = _create_user(db, "phase7-staff@example.test")

    business_a = create_business(
        db, BusinessCreate(name="Phase 7 Business A", business_type=BusinessType.INDEPENDENT), owner_a
    )
    business_b = create_business(
        db, BusinessCreate(name="Phase 7 Business B", business_type=BusinessType.INDEPENDENT), owner_b
    )
    branch_a1 = create_branch(db, business_a, BranchCreate(name="A One", country="NG"))
    branch_a2 = create_branch(db, business_a, BranchCreate(name="A Two", country="NG"))
    branch_b1 = create_branch(db, business_b, BranchCreate(name="B One", country="NG"))

    create_membership(
        db, business_a,
        MembershipCreate(user_id=staff.id, role=BusinessRole.KITCHEN_STAFF, branch_id=branch_a1.id),
        BusinessRole.OWNER,
    )

    assert can_access_branch(db, staff, branch_a1)
    assert not can_access_branch(db, staff, branch_a2)
    assert not can_access_branch(db, staff, branch_b1)
    assert not can_access_business(db, staff, business_b.id)


def test_suspended_membership_revokes_branch_access_immediately(db_session_fixture):
    db = db_session_fixture
    owner = _create_user(db, "phase7-owner@example.test")
    staff = _create_user(db, "phase7-suspended@example.test")
    business = create_business(
        db, BusinessCreate(name="Phase 7 Suspensions", business_type=BusinessType.INDEPENDENT), owner
    )
    branch = create_branch(db, business, BranchCreate(name="Main", country="NG"))
    membership = create_membership(
        db, business,
        MembershipCreate(user_id=staff.id, role=BusinessRole.COLLECTION_STAFF, branch_id=branch.id),
        BusinessRole.OWNER,
    )

    membership.is_active = False
    db.add(membership)
    db.commit()

    assert not can_access_branch(db, staff, branch)
    assert not can_access_business(db, staff, business.id)
