"""Business (tenant) ORM model supporting independent restaurants and franchises."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BusinessType(str, Enum):
    INDEPENDENT = "independent"
    FRANCHISE = "franchise"


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    business_type: Mapped[BusinessType] = mapped_column(
        SQLEnum(BusinessType, name="business_type"), nullable=False, default=BusinessType.INDEPENDENT
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[List["BusinessMembership"]] = relationship(
        "BusinessMembership", back_populates="business", cascade="all, delete-orphan"
    )
    branches: Mapped[List["Branch"]] = relationship(
        "Branch", back_populates="business", cascade="all, delete-orphan"
    )
