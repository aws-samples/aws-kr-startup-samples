"""add user monthly budget

Revision ID: 003
Revises: 002
Create Date: 2025-01-02
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("monthly_budget_usd", sa.Numeric(12, 2), nullable=True),
    )
    op.create_index(
        "idx_users_budget",
        "users",
        ["monthly_budget_usd"],
        unique=False,
        postgresql_where=sa.text("monthly_budget_usd IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_users_budget", table_name="users")
    op.drop_column("users", "monthly_budget_usd")
