"""add model slots and pricing catalog

Revision ID: 011
Revises: 010
Create Date: 2026-03-19
"""

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE model_slots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slot VARCHAR(20) NOT NULL UNIQUE,
            bedrock_model_id VARCHAR(128) NOT NULL,
            description TEXT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX idx_model_slots_slot ON model_slots (slot)")

    op.execute(
        """
        INSERT INTO model_slots (slot, bedrock_model_id, description, updated_at)
        VALUES
            (
                'opus',
                COALESCE(
                    (SELECT bedrock_model FROM model_mappings WHERE claude_model = 'claude-opus-4-6-v1' LIMIT 1),
                    'global.anthropic.claude-opus-4-6-v1'
                ),
                'Default Opus slot',
                now()
            ),
            (
                'sonnet',
                COALESCE(
                    (SELECT bedrock_model FROM model_mappings WHERE claude_model = 'claude-sonnet-4-6' LIMIT 1),
                    'global.anthropic.claude-sonnet-4-6'
                ),
                'Default Sonnet slot',
                now()
            ),
            (
                'haiku',
                COALESCE(
                    (SELECT bedrock_model FROM model_mappings WHERE claude_model = 'claude-haiku-4-5-20251001' LIMIT 1),
                    'global.anthropic.claude-haiku-4-5-20251001-v1:0'
                ),
                'Default Haiku slot',
                now()
            )
        """
    )

    op.execute(
        """
        CREATE TABLE model_pricing_catalog (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider VARCHAR(10) NOT NULL,
            region VARCHAR(32) NOT NULL,
            model_id VARCHAR(128) NOT NULL,
            input_price_per_million NUMERIC(12, 6) NOT NULL,
            output_price_per_million NUMERIC(12, 6) NOT NULL,
            cache_write_price_per_million NUMERIC(12, 6) NOT NULL,
            cache_read_price_per_million NUMERIC(12, 6) NOT NULL,
            effective_date DATE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            updated_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_model_pricing_catalog UNIQUE (provider, region, model_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_model_pricing_catalog_lookup ON model_pricing_catalog (provider, region, model_id)"
    )

    op.execute(
        """
        INSERT INTO model_pricing_catalog (
            provider,
            region,
            model_id,
            input_price_per_million,
            output_price_per_million,
            cache_write_price_per_million,
            cache_read_price_per_million,
            effective_date,
            is_active,
            updated_at
        )
        VALUES
            ('bedrock', 'ap-northeast-2', 'global.anthropic.claude-opus-4-5-20251101-v1:0', 5.00, 25.00, 6.25, 0.50, '2025-01-01', true, now()),
            ('bedrock', 'ap-northeast-2', 'global.anthropic.claude-opus-4-6-v1', 5.00, 25.00, 6.25, 0.50, '2025-01-01', true, now()),
            ('bedrock', 'ap-northeast-2', 'global.anthropic.claude-sonnet-4-5-20250929-v1:0', 3.00, 15.00, 3.75, 0.30, '2025-01-01', true, now()),
            ('bedrock', 'ap-northeast-2', 'global.anthropic.claude-sonnet-4-6', 3.00, 15.00, 3.75, 0.30, '2025-01-01', true, now()),
            ('bedrock', 'ap-northeast-2', 'global.anthropic.claude-haiku-4-5-20251001-v1:0', 1.00, 5.00, 1.25, 0.10, '2025-01-01', true, now()),
            ('plan', 'global', 'claude-opus-4-5-20251101', 5.00, 25.00, 6.25, 0.50, '2025-01-01', true, now()),
            ('plan', 'global', 'claude-opus-4-6-v1', 5.00, 25.00, 6.25, 0.50, '2025-01-01', true, now()),
            ('plan', 'global', 'claude-sonnet-4-5-20250929', 3.00, 15.00, 3.75, 0.30, '2025-01-01', true, now()),
            ('plan', 'global', 'claude-sonnet-4-6', 3.00, 15.00, 3.75, 0.30, '2025-01-01', true, now()),
            ('plan', 'global', 'claude-haiku-4-5-20251001', 1.00, 5.00, 1.25, 0.10, '2025-01-01', true, now())
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_model_pricing_catalog_lookup")
    op.execute("DROP TABLE IF EXISTS model_pricing_catalog")
    op.execute("DROP INDEX IF EXISTS idx_model_slots_slot")
    op.execute("DROP TABLE IF EXISTS model_slots")
