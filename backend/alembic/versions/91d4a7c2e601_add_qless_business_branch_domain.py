"""Add Qless business, branch, membership and branch QR tables.

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


business_type = sa.Enum("independent", "franchise", name="business_type")
business_role = sa.Enum(
    "owner", "franchise_admin", "branch_manager", "cashier", "kitchen_staff",
    "collection_staff", name="business_role"
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        raise RuntimeError(
            "Qless Phase 1 requires the existing users table. The repository's original "
            "Alembic baseline is empty; initialize the legacy schema or stamp a verified "
            "existing schema before applying this migration. Do not stamp an empty database."
        )

    business_type.create(bind, checkfirst=True)
    business_role.create(bind, checkfirst=True)

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
        unique=True, postgresql_where=sa.text("branch_id IS NULL")
    )
    op.create_index(
        "uq_membership_business_user_branch", "business_memberships", ["user_id", "business_id", "branch_id"],
        unique=True, postgresql_where=sa.text("branch_id IS NOT NULL")
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
