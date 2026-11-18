"""Tests for the Qless Phase 1 business/branch tenant foundation."""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserRole
from app.models.business import BusinessType
from app.models.business_membership import BusinessMembership, BusinessRole
from app.schemas.business import BusinessCreate, BranchCreate, MembershipCreate
from app.services.business_service import (
    can_access_branch, can_access_business, create_branch, create_business,
    create_membership, get_membership,
)


def _user(db, email: str) -> User:
    user = User(id=uuid.uuid4(), email=email, password_hash="test-hash", role=UserRole.CUSTOMER)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_business_assigns_creator_as_owner(db_session_fixture):
    owner = _user(db_session_fixture, "owner@example.test")
    business = create_business(
        db_session_fixture,
        BusinessCreate(name="Ada Kitchen", business_type=BusinessType.INDEPENDENT),
        owner,
    )

    membership = get_membership(db_session_fixture, owner.id, business.id)
    assert business.name == "Ada Kitchen"
    assert business.slug.startswith("ada-kitchen")
    assert membership is not None
    assert membership.role == BusinessRole.OWNER
    assert membership.branch_id is None


def test_branch_gets_permanent_branch_qr_and_staff_scope_is_enforced(db_session_fixture):
    owner = _user(db_session_fixture, "owner2@example.test")
    staff = _user(db_session_fixture, "staff@example.test")
    business = create_business(db_session_fixture, BusinessCreate(name="Qless Foods"), owner)
    branch_one = create_branch(
        db_session_fixture, business,
        BranchCreate(name="Ikeja", city="Ikeja", state="Lagos"),
    )
    branch_two = create_branch(
        db_session_fixture, business,
        BranchCreate(name="Yaba", city="Lagos", state="Lagos"),
    )

    assert branch_one.qr_code is not None
    assert branch_one.qr_code.token != branch_two.qr_code.token

    membership = create_membership(
        db_session_fixture, business,
        MembershipCreate(user_id=staff.id, role=BusinessRole.KITCHEN_STAFF, branch_id=branch_one.id),
        BusinessRole.OWNER,
    )
    assert membership.branch_id == branch_one.id
    assert can_access_branch(db_session_fixture, staff, branch_one)
    assert not can_access_branch(db_session_fixture, staff, branch_two)
    assert can_access_business(db_session_fixture, staff, business.id)
    assert get_membership(db_session_fixture, staff.id, business.id) is None


def test_branch_scoped_role_cannot_be_created_without_branch(db_session_fixture):
    owner = _user(db_session_fixture, "owner3@example.test")
    staff = _user(db_session_fixture, "staff2@example.test")
    business = create_business(db_session_fixture, BusinessCreate(name="Test Restaurant"), owner)

    with pytest.raises(ValueError, match="require a branch_id"):
        create_membership(
            db_session_fixture, business,
            MembershipCreate(user_id=staff.id, role=BusinessRole.CASHIER),
            BusinessRole.OWNER,
        )
