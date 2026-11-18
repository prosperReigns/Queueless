"""Add order fulfillment and single-use collection credentials.

Revision ID: e6f2a9c4d810
Revises: d4b8e1a6c903
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e6f2a9c4d810"
down_revision: Union[str, None] = "d4b8e1a6c903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_fulfillments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="awaiting_preparation"),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("order_id", name="uq_order_fulfillment_order"),
    )
    op.create_index("ix_order_fulfillments_branch_status", "order_fulfillments", ["branch_id", "status"])
    op.create_table(
        "collection_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("pin_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="issued"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("redemption_method", sa.String(20), nullable=True),
        sa.Column("handoff_name", sa.String(160), nullable=True),
        sa.Column("handoff_phone", sa.String(40), nullable=True),
        sa.UniqueConstraint("order_id", name="uq_collection_credential_order"),
    )
    op.create_index("ix_collection_credentials_token_hash", "collection_credentials", ["token_hash"], unique=True)
    op.create_index("ix_collection_credentials_pin_hash", "collection_credentials", ["pin_hash"], unique=True)
    op.create_table(
        "fulfillment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_fulfillment_events_branch_id", "fulfillment_events", ["branch_id", "id"])
    op.create_index("ix_fulfillment_events_order_id", "fulfillment_events", ["order_id"])
    op.execute("""
        INSERT INTO order_fulfillments (order_id, branch_id, method, status, ready_at, updated_at)
        SELECT o.id, o.branch_id, o.fulfillment_method,
               CASE WHEN kt.status = 'ready' THEN 'ready_for_collection' ELSE 'awaiting_preparation' END,
               CASE WHEN kt.status = 'ready' THEN kt.ready_at ELSE NULL END, now()
        FROM orders o
        LEFT JOIN kitchen_tickets kt ON kt.order_id = o.id
        WHERE o.branch_id IS NOT NULL AND o.fulfillment_method IS NOT NULL
        ON CONFLICT (order_id) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("ix_fulfillment_events_order_id", table_name="fulfillment_events")
    op.drop_index("ix_fulfillment_events_branch_id", table_name="fulfillment_events")
    op.drop_table("fulfillment_events")
    op.drop_index("ix_collection_credentials_pin_hash", table_name="collection_credentials")
    op.drop_index("ix_collection_credentials_token_hash", table_name="collection_credentials")
    op.drop_table("collection_credentials")
    op.drop_index("ix_order_fulfillments_branch_status", table_name="order_fulfillments")
    op.drop_table("order_fulfillments")
