"""Create missing legacy baseline tables and add Qless business/branch domain.

Revision ID: 91d4a7c2e601
Revises: 4bfa6bf1f138
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "91d4a7c2e601"
down_revision: Union[str, None] = "4bfa6bf1f138"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = sa.Enum("CUSTOMER", "MERCHANT", "ADMIN", name="user_role")
order_status = sa.Enum("PENDING", "PAID", "PREPARING", "READY", "COMPLETED", "CANCELLED", name="order_status")
payment_status = sa.Enum("PENDING", "SUCCESS", "FAILED", name="payment_status")
payment_provider = sa.Enum("PAYSTACK", name="payment_provider")
business_type = sa.Enum("independent", "franchise", name="business_type")
business_role = sa.Enum(
    "owner", "franchise_admin", "branch_manager", "cashier", "kitchen_staff",
    "collection_staff", name="business_role"
)


def _ensure_legacy_schema(bind) -> None:
    """Create legacy tables only when absent, allowing fresh installs and existing DBs."""
    for enum_type in (user_role, order_status, payment_status, payment_provider, business_type, business_role):
        enum_type.create(bind, checkfirst=True)

    if not sa.inspect(bind).has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("role", user_role, nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("email", name="uq_users_email"),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not sa.inspect(bind).has_table("stores"):
        op.create_table(
            "stores",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("location", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_stores_owner_id", "stores", ["owner_id"])

    if not sa.inspect(bind).has_table("products"):
        op.create_table(
            "products",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("price", sa.Numeric(10, 2), nullable=False),
            sa.Column("is_available", sa.Boolean(), nullable=False),
            sa.Column("image_url", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
        )
        op.create_index("ix_products_store_id", "products", ["store_id"])

    if not sa.inspect(bind).has_table("orders"):
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("status", order_status, nullable=False),
            sa.Column("payment_reference", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("total_amount >= 0", name="ck_orders_total_amount_non_negative"),
            sa.UniqueConstraint("payment_reference", name="uq_orders_payment_reference"),
        )
        op.create_index("ix_orders_user_id", "orders", ["user_id"])
        op.create_index("ix_orders_store_id", "orders", ["store_id"])
        op.create_index("ix_orders_payment_reference", "orders", ["payment_reference"], unique=True)

    if not sa.inspect(bind).has_table("order_items"):
        op.create_table(
            "order_items",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("price", sa.Numeric(10, 2), nullable=False),
            sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        )
        op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
        op.create_index("ix_order_items_product_id", "order_items", ["product_id"])

    if not sa.inspect(bind).has_table("payments"):
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reference", sa.String(255), nullable=False),
            sa.Column("status", payment_status, nullable=False),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("provider", payment_provider, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
            sa.UniqueConstraint("reference", name="uq_payments_reference"),
        )
        op.create_index("ix_payments_order_id", "payments", ["order_id"])
        op.create_index("ix_payments_reference", "payments", ["reference"], unique=True)

    if not sa.inspect(bind).has_table("notification_tokens"):
        op.create_table(
            "notification_tokens",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token", sa.String(1024), nullable=False),
            sa.Column("device_type", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("token", name="uq_notification_tokens_token"),
        )
        op.create_index("ix_notification_tokens_user_id", "notification_tokens", ["user_id"])
        op.create_index("ix_notification_tokens_token", "notification_tokens", ["token"], unique=True)


def upgrade() -> None:
    bind = op.get_bind()
    _ensure_legacy_schema(bind)

    op.create_table(
        "businesses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("business_type", business_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_businesses_slug"),
    )
    op.create_index("ix_businesses_slug", "businesses", ["slug"], unique=True)

    op.create_table(
        "branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("address_line", sa.String(255), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("state", sa.String(120), nullable=True),
        sa.Column("country", sa.String(2), server_default="NG", nullable=False),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("timezone", sa.String(64), server_default="Africa/Lagos", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("business_id", "slug", name="uq_branch_business_slug"),
    )
    op.create_index("ix_branches_business_id", "branches", ["business_id"])

    op.create_table(
        "business_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role", business_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(role IN ('owner', 'franchise_admin') AND branch_id IS NULL) OR "
            "(role IN ('branch_manager', 'cashier', 'kitchen_staff', 'collection_staff') AND branch_id IS NOT NULL)",
            name="ck_membership_role_scope",
        ),
    )
    op.create_index("ix_business_memberships_user_id", "business_memberships", ["user_id"])
    op.create_index("ix_business_memberships_business_id", "business_memberships", ["business_id"])
    op.create_index("ix_business_memberships_branch_id", "business_memberships", ["branch_id"])
    op.create_index(
        "uq_membership_business_user_global", "business_memberships", ["user_id", "business_id"],
        unique=True, postgresql_where=sa.text("branch_id IS NULL AND is_active IS TRUE")
    )
    op.create_index(
        "uq_membership_business_user_branch", "business_memberships", ["user_id", "business_id", "branch_id"],
        unique=True, postgresql_where=sa.text("branch_id IS NOT NULL AND is_active IS TRUE")
    )

    op.create_table(
        "branch_qr_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("branch_id", name="uq_branch_qr_codes_branch_id"),
        sa.UniqueConstraint("token", name="uq_branch_qr_codes_token"),
    )
    op.create_index("ix_branch_qr_codes_branch_id", "branch_qr_codes", ["branch_id"], unique=True)
    op.create_index("ix_branch_qr_codes_token", "branch_qr_codes", ["token"], unique=True)


def downgrade() -> None:
    # Remove only the Qless Phase 1 tables. Keep the legacy baseline tables intact.
    op.drop_index("ix_branch_qr_codes_token", table_name="branch_qr_codes")
    op.drop_index("ix_branch_qr_codes_branch_id", table_name="branch_qr_codes")
    op.drop_table("branch_qr_codes")
    op.drop_index("uq_membership_business_user_branch", table_name="business_memberships")
    op.drop_index("uq_membership_business_user_global", table_name="business_memberships")
    op.drop_index("ix_business_memberships_branch_id", table_name="business_memberships")
    op.drop_index("ix_business_memberships_business_id", table_name="business_memberships")
    op.drop_index("ix_business_memberships_user_id", table_name="business_memberships")
    op.drop_table("business_memberships")
    op.drop_index("ix_branches_business_id", table_name="branches")
    op.drop_table("branches")
    op.drop_index("ix_businesses_slug", table_name="businesses")
    op.drop_table("businesses")
    business_role.drop(op.get_bind(), checkfirst=True)
    business_type.drop(op.get_bind(), checkfirst=True)
