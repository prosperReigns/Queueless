"""User ORM model."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, Enum):
    """Application user role."""

    CUSTOMER = "customer"
    MERCHANT = "merchant"
    ADMIN = "admin"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.CUSTOMER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    stores: Mapped[list["Store"]] = relationship(
        "Store",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
