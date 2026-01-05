from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    String,
    Text,
    Integer,
    BigInteger,
    Boolean,
    LargeBinary,
    ForeignKey,
    Index,
    Numeric,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    routing_strategy: Mapped[str] = mapped_column(
        String(20), nullable=False, default="plan_first"
    )
    monthly_budget_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    access_keys: Mapped[list["AccessKeyModel"]] = relationship(back_populates="user")


class AccessKeyModel(Base):
    __tablename__ = "access_keys"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    bedrock_region: Mapped[str] = mapped_column(String(32), nullable=False)
    bedrock_model: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    rotation_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    user: Mapped["UserModel"] = relationship(back_populates="access_keys")
    bedrock_key: Mapped["BedrockKeyModel | None"] = relationship(back_populates="access_key")

    __table_args__ = (Index("idx_access_keys_user_id", "user_id"),)


class BedrockKeyModel(Base):
    __tablename__ = "bedrock_keys"

    access_key_id: Mapped[UUID] = mapped_column(
        ForeignKey("access_keys.id"), primary_key=True
    )
    encrypted_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    access_key: Mapped["AccessKeyModel"] = relationship(back_populates="bedrock_key")


class TokenUsageModel(Base):
    __tablename__ = "token_usage"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    access_key_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cache_read_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cache_creation_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(10), nullable=False, default="bedrock")
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0")
    )
    input_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0")
    )
    output_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0")
    )
    cache_write_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0")
    )
    cache_read_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0")
    )
    pricing_region: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ap-northeast-2"
    )
    pricing_model_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    pricing_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pricing_input_price_per_million: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0")
    )
    pricing_output_price_per_million: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0")
    )
    pricing_cache_write_price_per_million: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0")
    )
    pricing_cache_read_price_per_million: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0")
    )

    __table_args__ = (
        Index("idx_token_usage_timestamp", "timestamp"),
        Index("idx_token_usage_user_timestamp", "user_id", "timestamp"),
        Index("idx_token_usage_access_key_timestamp", "access_key_id", "timestamp"),
    )


class UsageAggregateModel(Base):
    __tablename__ = "usage_aggregates"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    bucket_type: Mapped[str] = mapped_column(String(10), nullable=False)
    bucket_start: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    access_key_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    total_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_cache_write_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_cache_read_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_input_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(15, 6), nullable=False, default=Decimal("0")
    )
    total_output_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(15, 6), nullable=False, default=Decimal("0")
    )
    total_cache_write_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(15, 6), nullable=False, default=Decimal("0")
    )
    total_cache_read_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(15, 6), nullable=False, default=Decimal("0")
    )
    total_estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(15, 6), nullable=False, default=Decimal("0")
    )

    __table_args__ = (
        Index("idx_usage_aggregates_lookup", "bucket_type", "bucket_start", "user_id"),
    )
