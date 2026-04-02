"""Payment ORM model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PaymentStatus(str, Enum):
    """Payment processing status."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class PaymentProvider(str, Enum):
    """Supported payment provider."""

    PAYSTACK = "paystack"


class Payment(Base):
    """Order payment transaction model."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    provider: Mapped[PaymentProvider] = mapped_column(
        SQLEnum(PaymentProvider, name="payment_provider"),
        nullable=False,
        default=PaymentProvider.PAYSTACK,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    order: Mapped["Order"] = relationship("Order", back_populates="payments")
