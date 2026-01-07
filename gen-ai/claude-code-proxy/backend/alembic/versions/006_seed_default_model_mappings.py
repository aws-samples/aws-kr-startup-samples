"""seed default model mappings

Revision ID: 006
Revises: 005
Create Date: 2025-01-07
"""

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Seed default model mappings
    # Uses ON CONFLICT DO NOTHING to be idempotent (safe to run multiple times)
    op.execute("""
        INSERT INTO model_mappings (id, claude_model, bedrock_model, description, is_active, created_at, updated_at)
        VALUES 
            (gen_random_uuid(), 'claude-haiku-4-5-20251001', 'global.anthropic.claude-haiku-4-5-20251001-v1:0', 'Claude Haiku 4.5 (default)', true, now(), now()),
            (gen_random_uuid(), 'claude-sonnet-4-5-20250929', 'global.anthropic.claude-sonnet-4-5-20250929-v1:0', 'Claude Sonnet 4.5 (default)', true, now(), now()),
            (gen_random_uuid(), 'claude-opus-4-5-20251101', 'global.anthropic.claude-opus-4-5-20251101-v1:0', 'Claude Opus 4.5 (default)', true, now(), now())
        ON CONFLICT (claude_model) DO NOTHING
    """)


def downgrade() -> None:
    # Remove the seeded default mappings
    op.execute("""
        DELETE FROM model_mappings 
        WHERE claude_model IN (
            'claude-haiku-4-5-20251001',
            'claude-sonnet-4-5-20250929',
            'claude-opus-4-5-20251101'
        )
        AND description LIKE '%(default)%'
    """)
