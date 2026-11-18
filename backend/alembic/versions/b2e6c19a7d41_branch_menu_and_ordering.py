"""Add business menus and branch-aware order metadata.

Revision ID: b2e6c19a7d41
Revises: 91d4a7c2e601
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2e6c19a7d41"
down_revision: Union[str, None] = "91d4a7c2e601"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

order_source = sa.Enum("preorder", "onsite_qr", name="order_source")
fulfillment_method = sa.Enum("self_collection", "external_rider", name="fulfillment_method")

def upgrade() -> None:
    bind = op.get_bind()
    order_source.create(bind, checkfirst=True)
    fulfillment_method.create(bind, checkfirst=True)

    op.create_table(
        "menu_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_menu_categories_business_id", "menu_categories", ["business_id"])

    op.create_table(
        "menu_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("menu_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("base_price > 0", name="ck_menu_items_base_price_positive"),
    )
    op.create_index("ix_menu_items_business_id", "menu_items", ["business_id"])
    op.create_index("ix_menu_items_category_id", "menu_items", ["category_id"])

    op.create_table(
        "branch_menu_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("menu_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("price_override", sa.Numeric(10, 2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("branch_id", "menu_item_id", name="uq_branch_menu_item"),
        sa.CheckConstraint("price_override IS NULL OR price_override > 0", name="ck_branch_menu_price_positive"),
    )
    op.create_index("ix_branch_menu_items_branch_id", "branch_menu_items", ["branch_id"])
    op.create_index("ix_branch_menu_items_menu_item_id", "branch_menu_items", ["menu_item_id"])

    op.alter_column("orders", "user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("orders", "store_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("orders", sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True))
    op.add_column("orders", sa.Column("order_source", order_source, nullable=True))
    op.add_column("orders", sa.Column("fulfillment_method", fulfillment_method, nullable=True))
    op.add_column("orders", sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("customer_name", sa.String(160), nullable=True))
    op.add_column("orders", sa.Column("customer_email", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("customer_phone", sa.String(40), nullable=True))
    op.add_column("orders", sa.Column("guest_access_token_hash", sa.String(64), nullable=True))
    op.add_column("orders", sa.Column("guest_access_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_orders_branch_id", "orders", ["branch_id"])
    op.create_index("uq_orders_guest_access_token_hash", "orders", ["guest_access_token_hash"], unique=True)

    op.alter_column("order_items", "product_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("order_items", sa.Column("menu_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True))
    op.add_column("order_items", sa.Column("item_name", sa.String(255), nullable=True))
    op.create_index("ix_order_items_menu_item_id", "order_items", ["menu_item_id"])

def downgrade() -> None:
    # Existing branch orders must be migrated or removed before downgrading.
    op.drop_index("ix_order_items_menu_item_id", table_name="order_items")
    op.drop_column("order_items", "item_name")
    op.drop_column("order_items", "menu_item_id")
    op.alter_column("order_items", "product_id", existing_type=sa.Integer(), nullable=False)
    op.drop_index("uq_orders_guest_access_token_hash", table_name="orders")
    op.drop_index("ix_orders_branch_id", table_name="orders")
    for column in ("guest_access_token_expires_at", "guest_access_token_hash", "customer_phone", "customer_email", "customer_name", "scheduled_for", "fulfillment_method", "order_source", "branch_id"):
        op.drop_column("orders", column)
    op.alter_column("orders", "store_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("orders", "user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.drop_index("ix_branch_menu_items_menu_item_id", table_name="branch_menu_items")
    op.drop_index("ix_branch_menu_items_branch_id", table_name="branch_menu_items")
    op.drop_table("branch_menu_items")
    op.drop_index("ix_menu_items_category_id", table_name="menu_items")
    op.drop_index("ix_menu_items_business_id", table_name="menu_items")
    op.drop_table("menu_items")
    op.drop_index("ix_menu_categories_business_id", table_name="menu_categories")
    op.drop_table("menu_categories")
    fulfillment_method.drop(op.get_bind(), checkfirst=True)
    order_source.drop(op.get_bind(), checkfirst=True)
