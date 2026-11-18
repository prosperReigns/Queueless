"""Restaurant branch ORM model."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("business_id", "slug", name="uq_branch_business_slug"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    address_line: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="NG", server_default="NG")
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Africa/Lagos", server_default="Africa/Lagos")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    business: Mapped["Business"] = relationship("Business", back_populates="branches")
    memberships: Mapped[List["BusinessMembership"]] = relationship("BusinessMembership", back_populates="branch")
    qr_code: Mapped[Optional["BranchQRCode"]] = relationship("BranchQRCode", back_populates="branch", uselist=False, cascade="all, delete-orphan")
