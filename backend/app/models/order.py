"""Order ORM model with backward-compatible branch commerce fields."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
import uuid
from sqlalchemy import CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class OrderSource(str, Enum):
    PREORDER = "preorder"
    ONSITE_QR = "onsite_qr"

class FulfillmentMethod(str, Enum):
    SELF_COLLECTION = "self_collection"
    EXTERNAL_RIDER = "external_rider"

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("total_amount >= 0", name="ck_orders_total_amount_non_negative"), Index("uq_orders_guest_access_token_hash", "guest_access_token_hash", unique=True))
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    store_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    order_source: Mapped[Optional[OrderSource]] = mapped_column(SQLEnum(OrderSource, name="order_source", values_callable=lambda cls: [e.value for e in cls]), nullable=True)
    fulfillment_method: Mapped[Optional[FulfillmentMethod]] = mapped_column(SQLEnum(FulfillmentMethod, name="fulfillment_method", values_callable=lambda cls: [e.value for e in cls]), nullable=True)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    guest_access_token_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus, name="order_status"), nullable=False, default=OrderStatus.PENDING)
    payment_reference: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user: Mapped[Optional["User"]] = relationship("User", back_populates="orders")
    store: Mapped[Optional["Store"]] = relationship("Store", back_populates="orders")
    branch: Mapped[Optional["Branch"]] = relationship("Branch")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="order")
