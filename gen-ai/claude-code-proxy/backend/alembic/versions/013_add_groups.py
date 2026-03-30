"""add groups, group_usage_aggregates, users.group_id, access_keys.expires_at

Revision ID: 013
Revises: 012
Create Date: 2026-03-30
"""

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE groups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            monthly_budget_usd NUMERIC(12,2),
            allowed_models TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        ALTER TABLE users ADD COLUMN group_id UUID REFERENCES groups(id)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_users_group_id ON users(group_id)
        """
    )

    op.execute(
        """
        ALTER TABLE access_keys ADD COLUMN expires_at TIMESTAMPTZ
        """
    )

    op.execute(
        """
        CREATE TABLE group_usage_aggregates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bucket_type VARCHAR(10) NOT NULL,
            bucket_start TIMESTAMPTZ NOT NULL,
            group_id UUID NOT NULL REFERENCES groups(id),
            provider VARCHAR(10) NOT NULL DEFAULT 'bedrock',
            total_requests INT NOT NULL DEFAULT 0,
            total_input_tokens BIGINT NOT NULL DEFAULT 0,
            total_output_tokens BIGINT NOT NULL DEFAULT 0,
            total_tokens BIGINT NOT NULL DEFAULT 0,
            total_cache_write_tokens BIGINT NOT NULL DEFAULT 0,
            total_cache_read_tokens BIGINT NOT NULL DEFAULT 0,
            total_input_cost_usd NUMERIC(15,6) NOT NULL DEFAULT 0,
            total_output_cost_usd NUMERIC(15,6) NOT NULL DEFAULT 0,
            total_cache_write_cost_usd NUMERIC(15,6) NOT NULL DEFAULT 0,
            total_cache_read_cost_usd NUMERIC(15,6) NOT NULL DEFAULT 0,
            total_estimated_cost_usd NUMERIC(15,6) NOT NULL DEFAULT 0,
            UNIQUE (bucket_type, bucket_start, group_id, provider)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_group_usage_agg_lookup
        ON group_usage_aggregates(bucket_type, bucket_start, group_id, provider)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS group_usage_aggregates")
    op.execute("ALTER TABLE access_keys DROP COLUMN IF EXISTS expires_at")
    op.execute("DROP INDEX IF EXISTS idx_users_group_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS group_id")
    op.execute("DROP TABLE IF EXISTS groups")
