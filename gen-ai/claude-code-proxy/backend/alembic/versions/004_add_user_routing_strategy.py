"""add user routing strategy

Revision ID: 004
Revises: 003
Create Date: 2025-01-05
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "routing_strategy",
            sa.String(20),
            nullable=False,
            server_default="plan_first",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "routing_strategy")

