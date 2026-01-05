from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal
from datetime import datetime
from decimal import Decimal
from uuid import UUID


# Anthropic API compatible schemas
class AnthropicMessage(BaseModel):
    role: str
    content: str | list | dict


class AnthropicRequest(BaseModel):
    model: str
    messages: list[AnthropicMessage]
    max_tokens: int | None = 4096
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: list[str] | None = None
    stream: bool = False
    system: str | list | None = None
    metadata: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: dict[str, Any] | None = None
    thinking: dict[str, Any] | None = None
    original_model: str | None = None


class AnthropicUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None


class AnthropicResponse(BaseModel):
    id: str
    type: str = "message"
    role: str = "assistant"
    content: list[dict]
    model: str
    stop_reason: str | None = None
    stop_sequence: str | None = None
    usage: AnthropicUsage


class AnthropicError(BaseModel):
    type: str = "error"
    error: dict
    request_id: str | None = None


class AnthropicCountTokensResponse(BaseModel):
    input_tokens: int


# Admin API schemas
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    routing_strategy: Literal["plan_first", "bedrock_only"] = "plan_first"
    monthly_budget_usd: Decimal | None = Field(
        default=None, ge=Decimal("0.01"), le=Decimal("999999.99")
    )


class UserResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    status: str
    routing_strategy: str = "plan_first"
    monthly_budget_usd: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("monthly_budget_usd", mode="before")
    @classmethod
    def _coerce_budget(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return str(value)
        return value


class UserRoutingStrategyUpdate(BaseModel):
    routing_strategy: Literal["plan_first", "bedrock_only"]


class UserBudgetUpdate(BaseModel):
    monthly_budget_usd: Decimal | None = Field(
        default=None, ge=Decimal("0.01"), le=Decimal("999999.99")
    )


class UserBudgetResponse(BaseModel):
    user_id: UUID
    monthly_budget_usd: str | None
    current_usage_usd: str
    remaining_usd: str | None
    usage_percentage: float | None
    period_start: datetime
    period_end: datetime


class AccessKeyCreate(BaseModel):
    bedrock_region: str = "ap-northeast-2"
    bedrock_model: str | None = None


class AccessKeyResponse(BaseModel):
    id: UUID
    key_prefix: str
    status: str
    bedrock_region: str
    bedrock_model: str
    created_at: datetime
    raw_key: str | None = None  # Only on creation
    has_bedrock_key: bool = False


class BedrockKeyRegister(BaseModel):
    bedrock_api_key: str = Field(min_length=1)


class UsageQueryParams(BaseModel):
    user_id: UUID | None = None
    access_key_id: UUID | None = None
    bucket_type: str = "hour"
    start_time: datetime | None = None
    end_time: datetime | None = None


class ModelPricingResponse(BaseModel):
    model_id: str
    region: str
    input_price: str
    output_price: str
    cache_write_price: str
    cache_read_price: str
    effective_date: str


class PricingListResponse(BaseModel):
    models: list[ModelPricingResponse]
    region: str


class CostBreakdownByModel(BaseModel):
    model_id: str
    total_cost_usd: str
    input_cost_usd: str
    output_cost_usd: str
    cache_write_cost_usd: str
    cache_read_cost_usd: str


class UsageBucket(BaseModel):
    bucket_start: datetime
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    input_cost_usd: str
    output_cost_usd: str
    cache_write_cost_usd: str
    cache_read_cost_usd: str
    estimated_cost_usd: str


class UsageResponse(BaseModel):
    buckets: list[UsageBucket]
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cache_write_tokens: int
    total_cache_read_tokens: int
    total_input_cost_usd: str
    total_output_cost_usd: str
    total_cache_write_cost_usd: str
    total_cache_read_cost_usd: str
    estimated_cost_usd: str
    cost_breakdown: list[CostBreakdownByModel]


class UsageTopUser(BaseModel):
    user_id: UUID
    name: str
    total_tokens: int
    total_requests: int
