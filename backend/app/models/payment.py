"""Payment, webhook idempotency, audit and refund ORM models."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class PaymentProvider(str, Enum):
    PAYSTACK = "paystack"

class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint("amount_refunded >= 0 AND amount_refunded <= amount", name="ck_payments_refunded_range"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    reference: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[PaymentStatus] = mapped_column(SQLEnum(PaymentStatus, name="payment_status"), nullable=False, default=PaymentStatus.PENDING)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN", server_default="NGN")
    provider: Mapped[PaymentProvider] = mapped_column(SQLEnum(PaymentProvider, name="payment_provider"), nullable=False, default=PaymentProvider.PAYSTACK)
    provider_transaction_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    authorization_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    access_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    amount_refunded: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    order: Mapped["Order"] = relationship("Order", back_populates="payments")
    status_history: Mapped[list["PaymentStatusHistory"]] = relationship("PaymentStatusHistory", back_populates="payment", cascade="all, delete-orphan")
    refunds: Mapped[list["PaymentRefund"]] = relationship("PaymentRefund", back_populates="payment", cascade="all, delete-orphan")

class PaymentEvent(Base):
    """Deduplicates provider webhooks using a stable canonical event hash."""
    __tablename__ = "payment_events"
    __table_args__ = (UniqueConstraint("provider", "event_key", name="uq_payment_event_provider_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[PaymentProvider] = mapped_column(SQLEnum(PaymentProvider, name="payment_provider"), nullable=False)
    event_key: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    processing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class PaymentStatusHistory(Base):
    __tablename__ = "payment_status_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    payment: Mapped[Payment] = relationship("Payment", back_populates="status_history")

class PaymentRefund(Base):
    __tablename__ = "payment_refunds"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_payment_refunds_reference"),
        UniqueConstraint("idempotency_key", name="uq_payment_refunds_idempotency_key"),
        CheckConstraint("amount > 0", name="ck_payment_refunds_amount_positive"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)
    reference: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_refund_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    initiated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment: Mapped[Payment] = relationship("Payment", back_populates="refunds")
