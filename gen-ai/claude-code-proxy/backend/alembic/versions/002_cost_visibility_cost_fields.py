"""add cost visibility fields

Revision ID: 002
Revises: 001
Create Date: 2025-01-02
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "token_usage",
        sa.Column(
            "estimated_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "token_usage",
        sa.Column(
            "input_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "token_usage",
        sa.Column(
            "output_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "token_usage",
        sa.Column(
            "cache_write_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "token_usage",
        sa.Column(
            "cache_read_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "token_usage",
        sa.Column(
            "pricing_region",
            sa.String(32),
            nullable=False,
            server_default="ap-northeast-2",
        ),
    )
    op.add_column(
        "token_usage",
        sa.Column(
            "pricing_model_id", sa.String(64), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "token_usage",
        sa.Column("pricing_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "token_usage",
        sa.Column(
            "pricing_input_price_per_million",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "token_usage",
        sa.Column(
            "pricing_output_price_per_million",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "token_usage",
        sa.Column(
            "pricing_cache_write_price_per_million",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "token_usage",
        sa.Column(
            "pricing_cache_read_price_per_million",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
    )

    op.add_column(
        "usage_aggregates",
        sa.Column(
            "total_cache_write_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "usage_aggregates",
        sa.Column(
            "total_cache_read_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "usage_aggregates",
        sa.Column(
            "total_input_cost_usd",
            sa.Numeric(15, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "usage_aggregates",
        sa.Column(
            "total_output_cost_usd",
            sa.Numeric(15, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "usage_aggregates",
        sa.Column(
            "total_cache_write_cost_usd",
            sa.Numeric(15, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "usage_aggregates",
        sa.Column(
            "total_cache_read_cost_usd",
            sa.Numeric(15, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "usage_aggregates",
        sa.Column(
            "total_estimated_cost_usd",
            sa.Numeric(15, 6),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("usage_aggregates", "total_estimated_cost_usd")
    op.drop_column("usage_aggregates", "total_cache_read_cost_usd")
    op.drop_column("usage_aggregates", "total_cache_write_cost_usd")
    op.drop_column("usage_aggregates", "total_output_cost_usd")
    op.drop_column("usage_aggregates", "total_input_cost_usd")
    op.drop_column("usage_aggregates", "total_cache_read_tokens")
    op.drop_column("usage_aggregates", "total_cache_write_tokens")

    op.drop_column("token_usage", "pricing_cache_read_price_per_million")
    op.drop_column("token_usage", "pricing_cache_write_price_per_million")
    op.drop_column("token_usage", "pricing_output_price_per_million")
    op.drop_column("token_usage", "pricing_input_price_per_million")
    op.drop_column("token_usage", "pricing_effective_date")
    op.drop_column("token_usage", "pricing_model_id")
    op.drop_column("token_usage", "pricing_region")
    op.drop_column("token_usage", "cache_read_cost_usd")
    op.drop_column("token_usage", "cache_write_cost_usd")
    op.drop_column("token_usage", "output_cost_usd")
    op.drop_column("token_usage", "input_cost_usd")
    op.drop_column("token_usage", "estimated_cost_usd")
