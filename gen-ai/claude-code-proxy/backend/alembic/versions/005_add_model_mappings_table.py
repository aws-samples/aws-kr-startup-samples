"""add model_mappings table

Revision ID: 005
Revises: 004
Create Date: 2025-01-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("claude_model", sa.String(128), nullable=False, unique=True),
        sa.Column("bedrock_model", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_model_mappings_claude_model",
        "model_mappings",
        ["claude_model"],
    )


def downgrade() -> None:
    op.drop_index("idx_model_mappings_claude_model", table_name="model_mappings")
    op.drop_table("model_mappings")
