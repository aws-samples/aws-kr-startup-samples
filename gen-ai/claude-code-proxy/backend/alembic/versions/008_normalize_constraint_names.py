"""normalize constraint names for existing deployments

Revision ID: 008
Revises: 007
Create Date: 2025-01-23
"""
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    This migration handles existing deployments where Migration 001 was run
    with auto-generated constraint names. It renames them to the new explicit names.
    
    This is safe to run multiple times (idempotent).
    """
    # Check if old auto-generated constraint exists and rename it
    # This handles databases that were created before we added explicit constraint names
    op.execute("""
        DO $$
        BEGIN
            -- Check if the old auto-generated constraint exists
            IF EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname LIKE 'usage_aggregates_bucket_type_bucket_start_user_id_access_ke%'
                AND conrelid = 'usage_aggregates'::regclass
            ) THEN
                -- Get the actual constraint name (it might be truncated)
                EXECUTE (
                    SELECT 'ALTER TABLE usage_aggregates RENAME CONSTRAINT ' || 
                           quote_ident(conname) || ' TO uq_usage_agg_bucket_key_prov'
                    FROM pg_constraint
                    WHERE conname LIKE 'usage_aggregates_bucket_type_bucket_start_user_id_access_ke%'
                    AND conrelid = 'usage_aggregates'::regclass
                    LIMIT 1
                );
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """
    Downgrade is intentionally a no-op because:
    1. The constraint functionality remains the same
    2. Reverting to auto-generated names would cause issues
    """
    pass
