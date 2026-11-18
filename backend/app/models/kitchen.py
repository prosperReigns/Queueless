"""Kitchen display tickets and durable branch-scoped events."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KitchenTicketStatus(str, Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"


class KitchenTicket(Base):
    __tablename__ = "kitchen_tickets"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_kitchen_ticket_order"),
        CheckConstraint("status IN ('new', 'accepted', 'preparing', 'ready')", name="ck_kitchen_ticket_status"),
        Index("ix_kitchen_tickets_branch_status_created", "branch_id", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[KitchenTicketStatus] = mapped_column(
        String(20), nullable=False, default=KitchenTicketStatus.NEW.value, server_default="new"
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preparing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    order: Mapped["Order"] = relationship("Order")


class KitchenEvent(Base):
    """Durable event log/outbox. Clients resume from the monotonically increasing id."""
    __tablename__ = "kitchen_events"
    __table_args__ = (
        Index("ix_kitchen_events_branch_id", "branch_id", "id"),
        Index("ix_kitchen_events_ticket_id", "ticket_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("kitchen_tickets.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
