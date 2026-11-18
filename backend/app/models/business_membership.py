"""Business and branch-scoped staff membership model."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey, Index, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class BusinessRole(str, Enum):
    OWNER = "owner"
    FRANCHISE_ADMIN = "franchise_admin"
    BRANCH_MANAGER = "branch_manager"
    CASHIER = "cashier"
    KITCHEN_STAFF = "kitchen_staff"
    COLLECTION_STAFF = "collection_staff"

class BusinessMembership(Base):
    __tablename__ = "business_memberships"
    __table_args__ = (
        CheckConstraint("(role IN ('owner', 'franchise_admin') AND branch_id IS NULL) OR (role IN ('branch_manager', 'cashier', 'kitchen_staff', 'collection_staff') AND branch_id IS NOT NULL)", name="ck_membership_role_scope"),
        Index("uq_membership_business_user_global", "user_id", "business_id", unique=True, postgresql_where=text("branch_id IS NULL AND is_active IS TRUE"), sqlite_where=text("branch_id IS NULL AND is_active = 1")),
        Index("uq_membership_business_user_branch", "user_id", "business_id", "branch_id", unique=True, postgresql_where=text("branch_id IS NOT NULL AND is_active IS TRUE"), sqlite_where=text("branch_id IS NOT NULL AND is_active = 1")),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=True, index=True)
    role: Mapped[BusinessRole] = mapped_column(SQLEnum(BusinessRole, name="business_role", values_callable=lambda cls: [item.value for item in cls]), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user: Mapped["User"] = relationship("User", back_populates="business_memberships")
    business: Mapped["Business"] = relationship("Business", back_populates="memberships")
    branch: Mapped[Optional["Branch"]] = relationship("Branch", back_populates="memberships")
