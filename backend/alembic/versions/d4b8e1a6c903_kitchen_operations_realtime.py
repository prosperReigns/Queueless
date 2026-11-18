"""Add branch kitchen tickets and durable event stream.

Revision ID: d4b8e1a6c903
Revises: c7a4d91e2f60
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4b8e1a6c903"
down_revision: Union[str, None] = "c7a4d91e2f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kitchen_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preparing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("order_id", name="uq_kitchen_ticket_order"),
        sa.CheckConstraint("status IN ('new', 'accepted', 'preparing', 'ready')", name="ck_kitchen_ticket_status"),
    )
    op.create_index("ix_kitchen_tickets_branch_status_created", "kitchen_tickets", ["branch_id", "status", "created_at"])

    op.create_table(
        "kitchen_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("kitchen_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_kitchen_events_branch_id", "kitchen_events", ["branch_id", "id"])
    op.create_index("ix_kitchen_events_ticket_id", "kitchen_events", ["ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_kitchen_events_ticket_id", table_name="kitchen_events")
    op.drop_index("ix_kitchen_events_branch_id", table_name="kitchen_events")
    op.drop_table("kitchen_events")
    op.drop_index("ix_kitchen_tickets_branch_status_created", table_name="kitchen_tickets")
    op.drop_table("kitchen_tickets")
