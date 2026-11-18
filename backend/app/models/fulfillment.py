"""Collection credentials and fulfillment state for branch orders."""
from __future__ import annotations
from datetime import datetime
import uuid
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class FulfillmentStatus:
    AWAITING_PREPARATION = "awaiting_preparation"
    READY_FOR_COLLECTION = "ready_for_collection"
    COLLECTED = "collected"
    RIDER_COLLECTED = "rider_collected"
    CANCELLED = "cancelled"

class CollectionCredentialStatus:
    ISSUED = "issued"
    REDEEMED = "redeemed"
    REVOKED = "revoked"
    EXPIRED = "expired"

class OrderFulfillment(Base):
    __tablename__ = "order_fulfillments"
    __table_args__ = (UniqueConstraint("order_id", name="uq_order_fulfillment_order"), Index("ix_order_fulfillments_branch_status", "branch_id", "status"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=FulfillmentStatus.AWAITING_PREPARATION, server_default=FulfillmentStatus.AWAITING_PREPARATION)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class CollectionCredential(Base):
    """Only hashes are persisted; the QR token and PIN are shown once on issuance."""
    __tablename__ = "collection_credentials"
    __table_args__ = (UniqueConstraint("order_id", name="uq_collection_credential_order"), Index("ix_collection_credentials_token_hash", "token_hash", unique=True), Index("ix_collection_credentials_pin_hash", "pin_hash", unique=True))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=CollectionCredentialStatus.ISSUED, server_default=CollectionCredentialStatus.ISSUED)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    redeemed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    redemption_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    handoff_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    handoff_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)

class FulfillmentEvent(Base):
    """Append-only audit events for credential issuance and physical handoff."""
    __tablename__ = "fulfillment_events"
    __table_args__ = (Index("ix_fulfillment_events_branch_id", "branch_id", "id"), Index("ix_fulfillment_events_order_id", "order_id"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
