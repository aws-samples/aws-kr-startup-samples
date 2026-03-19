"""update default models to 4.6

Revision ID: 010
Revises: 009
Create Date: 2026-03-18
"""

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO model_mappings (id, claude_model, bedrock_model, description, is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'claude-sonnet-4-6', 'global.anthropic.claude-sonnet-4-6', 'Claude Sonnet 4.6 (default)', true, now(), now()),
            (gen_random_uuid(), 'claude-opus-4-6-v1', 'global.anthropic.claude-opus-4-6-v1', 'Claude Opus 4.6 (default)', true, now(), now())
        ON CONFLICT (claude_model)
        DO UPDATE SET
            bedrock_model = EXCLUDED.bedrock_model,
            description = EXCLUDED.description,
            is_active = true,
            updated_at = now()
        """
    )

    op.execute(
        """
        UPDATE access_keys
        SET bedrock_model = 'global.anthropic.claude-sonnet-4-6'
        WHERE bedrock_model = 'global.anthropic.claude-sonnet-4-5-20250929-v1:0'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM model_mappings
        WHERE claude_model IN ('claude-sonnet-4-6', 'claude-opus-4-6-v1')
        AND description IN ('Claude Sonnet 4.6 (default)', 'Claude Opus 4.6 (default)')
        """
    )

    op.execute(
        """
        UPDATE access_keys
        SET bedrock_model = 'global.anthropic.claude-sonnet-4-5-20250929-v1:0'
        WHERE bedrock_model = 'global.anthropic.claude-sonnet-4-6'
        """
    )
