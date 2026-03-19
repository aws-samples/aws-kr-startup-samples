"""add one hour cache write pricing

Revision ID: 012
Revises: 011
Create Date: 2026-03-19
"""

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE model_pricing_catalog
        ADD COLUMN cache_write_1h_price_per_million NUMERIC(12, 6) NOT NULL DEFAULT 0
        """
    )

    op.execute(
        """
        UPDATE model_pricing_catalog
        SET cache_write_1h_price_per_million = CASE
            WHEN model_id IN ('global.anthropic.claude-opus-4-6-v1', 'claude-opus-4-6-v1') THEN 10.00
            WHEN model_id IN ('global.anthropic.claude-sonnet-4-6', 'claude-sonnet-4-6') THEN 6.00
            WHEN model_id IN ('global.anthropic.claude-haiku-4-5-20251001-v1:0', 'claude-haiku-4-5-20251001') THEN 2.00
            WHEN model_id IN ('global.anthropic.claude-opus-4-5-20251101-v1:0', 'claude-opus-4-5-20251101') THEN 10.00
            WHEN model_id IN ('global.anthropic.claude-sonnet-4-5-20250929-v1:0', 'claude-sonnet-4-5-20250929') THEN 6.00
            ELSE cache_write_price_per_million
        END,
        updated_at = now()
        """
    )

    op.execute(
        """
        UPDATE model_pricing_catalog
        SET is_active = false, updated_at = now()
        WHERE model_id IN (
            'global.anthropic.claude-opus-4-5-20251101-v1:0',
            'global.anthropic.claude-sonnet-4-5-20250929-v1:0',
            'claude-opus-4-5-20251101',
            'claude-sonnet-4-5-20250929'
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE model_pricing_catalog DROP COLUMN IF EXISTS cache_write_1h_price_per_million")
