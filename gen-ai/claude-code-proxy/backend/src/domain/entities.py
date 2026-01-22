from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from .enums import UserStatus, KeyStatus, RoutingStrategy
from .types import Provider


@dataclass
class User:
    id: UUID
    name: str
    description: str | None
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    routing_strategy: RoutingStrategy = RoutingStrategy.PLAN_FIRST
    monthly_budget_usd: Decimal | None = None
    deleted_at: datetime | None = None


@dataclass
class AccessKey:
    id: UUID
    user_id: UUID
    key_hash: str
    key_prefix: str
    status: KeyStatus
    bedrock_region: str
    bedrock_model: str
    created_at: datetime
    revoked_at: datetime | None = None
    rotation_expires_at: datetime | None = None


@dataclass
class BedrockKey:
    access_key_id: UUID
    encrypted_key: bytes
    key_hash: str
    created_at: datetime
    rotated_at: datetime | None = None


@dataclass
class TokenUsage:
    id: UUID
    request_id: str
    timestamp: datetime
    user_id: UUID
    access_key_id: UUID
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int | None
    cache_creation_input_tokens: int | None
    total_tokens: int
    provider: Provider
    is_fallback: bool
    latency_ms: int
    estimated_cost_usd: Decimal
    input_cost_usd: Decimal
    output_cost_usd: Decimal
    cache_write_cost_usd: Decimal
    cache_read_cost_usd: Decimal
    pricing_region: str
    pricing_model_id: str
    pricing_effective_date: date | None
    pricing_input_price_per_million: Decimal
    pricing_output_price_per_million: Decimal
    pricing_cache_write_price_per_million: Decimal
    pricing_cache_read_price_per_million: Decimal


@dataclass
class UsageAggregate:
    id: UUID
    bucket_type: str
    bucket_start: datetime
    user_id: UUID
    access_key_id: UUID | None
    provider: Provider
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cache_write_tokens: int
    total_cache_read_tokens: int
    total_input_cost_usd: Decimal
    total_output_cost_usd: Decimal
    total_cache_write_cost_usd: Decimal
    total_cache_read_cost_usd: Decimal
    total_estimated_cost_usd: Decimal
