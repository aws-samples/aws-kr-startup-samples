"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "access_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("bedrock_region", sa.String(32), nullable=False),
        sa.Column("bedrock_model", sa.String(128), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("rotation_expires_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("idx_access_keys_user_id", "access_keys", ["user_id"])

    op.create_table(
        "bedrock_keys",
        sa.Column("access_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("access_keys.id"), primary_key=True),
        sa.Column("encrypted_key", sa.LargeBinary, nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("rotated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "token_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(64), nullable=False, unique=True),
        sa.Column("timestamp", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_key_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("cache_read_input_tokens", sa.Integer, nullable=True),
        sa.Column("cache_creation_input_tokens", sa.Integer, nullable=True),
        sa.Column("total_tokens", sa.Integer, nullable=False),
        sa.Column("provider", sa.String(10), nullable=False, server_default="bedrock"),
        sa.Column("is_fallback", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("latency_ms", sa.Integer, nullable=False),
    )
    op.create_index("idx_token_usage_timestamp", "token_usage", ["timestamp"])
    op.create_index("idx_token_usage_user_timestamp", "token_usage", ["user_id", "timestamp"])
    op.create_index("idx_token_usage_access_key_timestamp", "token_usage", ["access_key_id", "timestamp"])

    op.create_table(
        "usage_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bucket_type", sa.String(10), nullable=False),
        sa.Column("bucket_start", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("total_requests", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_input_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_output_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.UniqueConstraint("bucket_type", "bucket_start", "user_id", "access_key_id"),
    )
    op.create_index("idx_usage_aggregates_lookup", "usage_aggregates", ["bucket_type", "bucket_start", "user_id"])


def downgrade() -> None:
    op.drop_table("usage_aggregates")
    op.drop_table("token_usage")
    op.drop_table("bedrock_keys")
    op.drop_table("access_keys")
    op.drop_table("users")
