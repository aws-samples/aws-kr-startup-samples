"""add user caching strategy

Revision ID: 009
Revises: 008
Create Date: 2026-03-18
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "caching_strategy",
            sa.String(10),
            nullable=False,
            server_default="5m",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "caching_strategy")
