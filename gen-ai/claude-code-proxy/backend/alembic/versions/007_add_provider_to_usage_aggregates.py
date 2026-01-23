"""add provider to usage aggregates

Revision ID: 007
Revises: 006
Create Date: 2025-02-01
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usage_aggregates",
        sa.Column(
            "provider",
            sa.String(10),
            nullable=False,
            server_default="bedrock",
        ),
    )
    op.execute("UPDATE usage_aggregates SET provider = 'bedrock' WHERE provider IS NULL")

    # Drop existing unique constraint - handle multiple possible names for backward compatibility
    # Try the new explicit name first (for fresh installs)
    op.execute(
        "ALTER TABLE usage_aggregates "
        "DROP CONSTRAINT IF EXISTS uq_usage_agg_bucket_key"
    )
    # Try PostgreSQL auto-generated names (for existing deployments)
    op.execute(
        "ALTER TABLE usage_aggregates "
        "DROP CONSTRAINT IF EXISTS usage_aggregates_bucket_type_bucket_start_user_id_access_key_id_key"
    )
    op.execute(
        "ALTER TABLE usage_aggregates "
        "DROP CONSTRAINT IF EXISTS usage_aggregates_bucket_type_bucket_start_user_id_access_ke_key"
    )

    # Create new unique constraint with provider
    op.create_unique_constraint(
        "uq_usage_agg_bucket_key_prov",
        "usage_aggregates",
        ["bucket_type", "bucket_start", "user_id", "access_key_id", "provider"],
    )

    # Recreate index with provider
    op.drop_index("idx_usage_aggregates_lookup", table_name="usage_aggregates")
    op.create_index(
        "idx_usage_aggregates_lookup",
        "usage_aggregates",
        ["bucket_type", "bucket_start", "user_id", "provider"],
    )


def downgrade() -> None:
    # Drop new constraint
    op.drop_constraint(
        "uq_usage_agg_bucket_key_prov",
        "usage_aggregates",
        type_="unique",
    )
    op.drop_index("idx_usage_aggregates_lookup", table_name="usage_aggregates")
    op.drop_column("usage_aggregates", "provider")
    
    # Recreate original constraint with explicit name
    op.create_unique_constraint(
        "uq_usage_agg_bucket_key",
        "usage_aggregates",
        ["bucket_type", "bucket_start", "user_id", "access_key_id"],
    )
    op.create_index(
        "idx_usage_aggregates_lookup",
        "usage_aggregates",
        ["bucket_type", "bucket_start", "user_id"],
    )
