"""Add payment verification, webhook idempotency, audit and refunds.

Revision ID: c7a4d91e2f60
Revises: b2e6c19a7d41
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c7a4d91e2f60"
down_revision: Union[str, None] = "b2e6c19a7d41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

payment_provider = postgresql.ENUM("PAYSTACK", name="payment_provider", create_type=False)

def upgrade() -> None:
    op.add_column("payments", sa.Column("currency", sa.String(3), nullable=False, server_default="NGN"))
    op.add_column("payments", sa.Column("provider_transaction_id", sa.String(64), nullable=True))
    op.add_column("payments", sa.Column("authorization_url", sa.String(2048), nullable=True))
    op.add_column("payments", sa.Column("access_code", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("failure_reason", sa.String(500), nullable=True))
    op.add_column("payments", sa.Column("amount_refunded", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("payments", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_payments_provider_transaction_id", "payments", ["provider_transaction_id"])
    op.create_check_constraint("ck_payments_refunded_range", "payments", "amount_refunded >= 0 AND amount_refunded <= amount")

    op.create_table(
        "payment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", payment_provider, nullable=False),
        sa.Column("event_key", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payment_reference", sa.String(255), nullable=True),
        sa.Column("processing_status", sa.String(20), nullable=False, server_default="received"),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("provider", "event_key", name="uq_payment_event_provider_key"),
    )
    op.create_index("ix_payment_events_payment_reference", "payment_events", ["payment_reference"])

    op.create_table(
        "payment_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payment_status_history_payment_id", "payment_status_history", ["payment_id"])

    op.create_table(
        "payment_refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("provider_refund_id", sa.String(64), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="NGN"),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("initiated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("reference", name="uq_payment_refunds_reference"),
        sa.UniqueConstraint("idempotency_key", name="uq_payment_refunds_idempotency_key"),
        sa.CheckConstraint("amount > 0", name="ck_payment_refunds_amount_positive"),
    )
    op.create_index("ix_payment_refunds_payment_id", "payment_refunds", ["payment_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_refunds_payment_id", table_name="payment_refunds")
    op.drop_table("payment_refunds")
    op.drop_index("ix_payment_status_history_payment_id", table_name="payment_status_history")
    op.drop_table("payment_status_history")
    op.drop_index("ix_payment_events_payment_reference", table_name="payment_events")
    op.drop_table("payment_events")
    op.drop_constraint("ck_payments_refunded_range", "payments", type_="check")
    op.drop_index("ix_payments_provider_transaction_id", table_name="payments")
    for column in ("updated_at", "amount_refunded", "failure_reason", "paid_at", "access_code", "authorization_url", "provider_transaction_id", "currency"):
        op.drop_column("payments", column)
