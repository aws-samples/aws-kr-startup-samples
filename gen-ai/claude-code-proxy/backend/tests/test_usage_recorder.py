from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.domain import AnthropicUsage
from src.domain.cost_calculator import CostCalculator
from src.domain.pricing import ModelPricing, PricingConfig
from src.proxy.context import RequestContext
from src.proxy.router import ProxyResponse
from src.proxy.usage import UsageRecorder
from hypothesis import given, strategies as st


class FakeTokenUsageRepository:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return kwargs


class FakeUsageAggregateRepository:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def increment(self, **kwargs) -> None:
        self.calls.append(kwargs)


@dataclass
class DummyMetricsEmitter:
    async def emit(self, *_args, **_kwargs) -> None:  # pragma: no cover - not invoked here
        return None


def _build_recorder_context(
    monkeypatch: pytest.MonkeyPatch, pricing: ModelPricing
) -> tuple[
    UsageRecorder,
    FakeTokenUsageRepository,
    FakeUsageAggregateRepository,
    RequestContext,
    ProxyResponse,
]:
    monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

    token_repo = FakeTokenUsageRepository()
    agg_repo = FakeUsageAggregateRepository()
    recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

    ctx = RequestContext(
        request_id="req-1",
        user_id=uuid4(),
        access_key_id=uuid4(),
        access_key_prefix="ak_test",
        bedrock_region="ap-northeast-2",
        bedrock_model="anthropic.claude-opus-4-5-20250514",
        has_bedrock_key=True,
    )
    usage = AnthropicUsage(
        input_tokens=100,
        output_tokens=50,
        cache_read_input_tokens=10,
        cache_creation_input_tokens=5,
    )
    response = ProxyResponse(
        success=True,
        response=None,
        usage=usage,
        provider="bedrock",
        is_fallback=False,
        status_code=200,
    )

    return recorder, token_repo, agg_repo, ctx, response


# Feature: cost-visibility, Property 4: Token Usage Recording Completeness
@pytest.mark.asyncio
async def test_record_usage_with_cost_stores_pricing_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pricing = ModelPricing(
        model_id="claude-opus-4-5",
        region="ap-northeast-2",
        input_price_per_million=Decimal("1.00"),
        output_price_per_million=Decimal("2.00"),
        cache_write_price_per_million=Decimal("3.00"),
        cache_read_price_per_million=Decimal("4.00"),
        effective_date=date(2025, 1, 1),
    )

    recorder, token_repo, _agg_repo, ctx, response = _build_recorder_context(monkeypatch, pricing)

    await recorder._record_usage_with_cost(
        ctx, response, latency_ms=123, model=ctx.bedrock_model, provider="bedrock"
    )

    assert len(token_repo.calls) == 1
    call = token_repo.calls[0]
    expected_costs = CostCalculator.calculate_cost(
        input_tokens=100,
        output_tokens=50,
        cache_write_tokens=5,
        cache_read_tokens=10,
        pricing=pricing,
    )

    assert call["estimated_cost_usd"] == expected_costs.total_cost
    assert call["input_cost_usd"] == expected_costs.input_cost
    assert call["output_cost_usd"] == expected_costs.output_cost
    assert call["cache_write_cost_usd"] == expected_costs.cache_write_cost
    assert call["cache_read_cost_usd"] == expected_costs.cache_read_cost
    assert call["pricing_model_id"] == "claude-opus-4-5"
    assert call["pricing_effective_date"] == date(2025, 1, 1)
    assert call["pricing_input_price_per_million"] == Decimal("1.00")
    assert call["pricing_output_price_per_million"] == Decimal("2.00")
    assert call["pricing_cache_write_price_per_million"] == Decimal("3.00")
    assert call["pricing_cache_read_price_per_million"] == Decimal("4.00")


# Feature: cost-visibility, Property 9: Aggregate Cache Token Tracking
@pytest.mark.asyncio
async def test_record_usage_with_cost_increments_aggregates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pricing = ModelPricing(
        model_id="claude-opus-4-5",
        region="ap-northeast-2",
        input_price_per_million=Decimal("1.00"),
        output_price_per_million=Decimal("2.00"),
        cache_write_price_per_million=Decimal("3.00"),
        cache_read_price_per_million=Decimal("4.00"),
        effective_date=date(2025, 1, 1),
    )
    recorder, _token_repo, agg_repo, ctx, response = _build_recorder_context(monkeypatch, pricing)

    await recorder._record_usage_with_cost(
        ctx, response, latency_ms=123, model=ctx.bedrock_model, provider="bedrock"
    )

    expected_costs = CostCalculator.calculate_cost(
        input_tokens=100,
        output_tokens=50,
        cache_write_tokens=5,
        cache_read_tokens=10,
        pricing=pricing,
    )

    assert len(agg_repo.calls) == 5
    for agg_call in agg_repo.calls:
        assert agg_call["cache_write_tokens"] == 5
        assert agg_call["cache_read_tokens"] == 10
        assert agg_call["total_estimated_cost_usd"] == expected_costs.total_cost
        assert agg_call["total_input_cost_usd"] == expected_costs.input_cost
        assert agg_call["total_output_cost_usd"] == expected_costs.output_cost
        assert agg_call["total_cache_write_cost_usd"] == expected_costs.cache_write_cost
        assert agg_call["total_cache_read_cost_usd"] == expected_costs.cache_read_cost
        assert agg_call["bucket_start"].tzinfo is not None


# Feature: cost-visibility, Property 8: Error Resilience
@pytest.mark.asyncio
async def test_record_usage_with_cost_falls_back_to_zero_on_pricing_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_error(*_args, **_kwargs):
        raise RuntimeError("pricing lookup failed")

    monkeypatch.setattr(PricingConfig, "get_pricing", _raise_error)

    token_repo = FakeTokenUsageRepository()
    agg_repo = FakeUsageAggregateRepository()
    recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

    ctx = RequestContext(
        request_id="req-2",
        user_id=uuid4(),
        access_key_id=uuid4(),
        access_key_prefix="ak_test",
        bedrock_region="ap-northeast-2",
        bedrock_model="anthropic.claude-sonnet-4-5-20250514",
        has_bedrock_key=True,
    )
    usage = AnthropicUsage(
        input_tokens=10,
        output_tokens=5,
        cache_read_input_tokens=None,
        cache_creation_input_tokens=None,
    )
    response = ProxyResponse(
        success=True,
        response=None,
        usage=usage,
        provider="bedrock",
        is_fallback=False,
        status_code=200,
    )

    await recorder._record_usage_with_cost(
        ctx, response, latency_ms=45, model=ctx.bedrock_model, provider="bedrock"
    )

    assert len(token_repo.calls) == 1
    call = token_repo.calls[0]

    assert call["estimated_cost_usd"] == Decimal("0.000000")
    assert call["input_cost_usd"] == Decimal("0.000000")
    assert call["output_cost_usd"] == Decimal("0.000000")
    assert call["cache_write_cost_usd"] == Decimal("0.000000")
    assert call["cache_read_cost_usd"] == Decimal("0.000000")
    assert call["pricing_model_id"] == "claude-sonnet-4-5"


@given(
    input_tokens=st.integers(min_value=0, max_value=1000),
    output_tokens=st.integers(min_value=0, max_value=1000),
    cache_write_tokens=st.integers(min_value=0, max_value=1000),
    cache_read_tokens=st.integers(min_value=0, max_value=1000),
)
@pytest.mark.asyncio
async def test_usage_accumulation_property(
    input_tokens: int,
    output_tokens: int,
    cache_write_tokens: int,
    cache_read_tokens: int,
) -> None:
    pricing = ModelPricing(
        model_id="claude-opus-4-5",
        region="ap-northeast-2",
        input_price_per_million=Decimal("1.00"),
        output_price_per_million=Decimal("2.00"),
        cache_write_price_per_million=Decimal("3.00"),
        cache_read_price_per_million=Decimal("4.00"),
        effective_date=date(2025, 1, 1),
    )

    with patch.object(PricingConfig, "get_pricing", return_value=pricing):
        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        ctx = RequestContext(
            request_id="req-prop",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak_test",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-opus-4-5-20250514",
            has_bedrock_key=True,
        )
        usage = AnthropicUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read_tokens,
            cache_creation_input_tokens=cache_write_tokens,
        )
        response = ProxyResponse(
            success=True,
            response=None,
            usage=usage,
            provider="bedrock",
            is_fallback=False,
            status_code=200,
        )

        await recorder._record_usage_with_cost(
            ctx,
            response,
            latency_ms=123,
            model=ctx.bedrock_model,
            provider="bedrock",
        )

        expected_costs = CostCalculator.calculate_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_write_tokens=cache_write_tokens,
            cache_read_tokens=cache_read_tokens,
            pricing=pricing,
        )

        assert agg_repo.calls
        for agg_call in agg_repo.calls:
            assert agg_call["total_estimated_cost_usd"] == expected_costs.total_cost


@pytest.mark.asyncio
async def test_plan_usage_recording_stores_provider_and_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pricing = ModelPricing(
        model_id="claude-opus-4-5",
        region="global",
        input_price_per_million=Decimal("4.00"),
        output_price_per_million=Decimal("20.00"),
        cache_write_price_per_million=Decimal("5.00"),
        cache_read_price_per_million=Decimal("0.40"),
        effective_date=date(2025, 1, 1),
    )
    monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

    token_repo = FakeTokenUsageRepository()
    agg_repo = FakeUsageAggregateRepository()
    recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

    ctx = RequestContext(
        request_id="req-plan",
        user_id=uuid4(),
        access_key_id=uuid4(),
        access_key_prefix="ak_plan",
        bedrock_region="ap-northeast-2",
        bedrock_model="claude-opus-4-5",
        has_bedrock_key=True,
    )
    usage = AnthropicUsage(
        input_tokens=120,
        output_tokens=60,
        cache_read_input_tokens=12,
        cache_creation_input_tokens=6,
    )
    response = ProxyResponse(
        success=True,
        response=None,
        usage=usage,
        provider="plan",
        is_fallback=False,
        status_code=200,
    )

    await recorder._record_usage_with_cost(
        ctx, response, latency_ms=80, model="claude-opus-4-5", provider="plan"
    )

    assert len(token_repo.calls) == 1
    call = token_repo.calls[0]
    assert call["provider"] == "plan"
    assert call["input_tokens"] == 120
    assert call["output_tokens"] == 60
    assert call["cache_read_input_tokens"] == 12
    assert call["cache_creation_input_tokens"] == 6
    assert all(agg_call["provider"] == "plan" for agg_call in agg_repo.calls)


@pytest.mark.asyncio
async def test_plan_pricing_used_for_cost_calculation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pricing = ModelPricing(
        model_id="claude-sonnet-4-5",
        region="global",
        input_price_per_million=Decimal("2.00"),
        output_price_per_million=Decimal("10.00"),
        cache_write_price_per_million=Decimal("2.50"),
        cache_read_price_per_million=Decimal("0.20"),
        effective_date=date(2025, 1, 1),
    )
    monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

    token_repo = FakeTokenUsageRepository()
    agg_repo = FakeUsageAggregateRepository()
    recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

    ctx = RequestContext(
        request_id="req-plan-cost",
        user_id=uuid4(),
        access_key_id=uuid4(),
        access_key_prefix="ak_plan",
        bedrock_region="ap-northeast-2",
        bedrock_model="claude-sonnet-4-5",
        has_bedrock_key=True,
    )
    usage = AnthropicUsage(
        input_tokens=1_000_000,
        output_tokens=500_000,
        cache_read_input_tokens=100_000,
        cache_creation_input_tokens=50_000,
    )
    response = ProxyResponse(
        success=True,
        response=None,
        usage=usage,
        provider="plan",
        is_fallback=False,
        status_code=200,
    )

    await recorder._record_usage_with_cost(
        ctx, response, latency_ms=120, model="claude-sonnet-4-5", provider="plan"
    )

    expected_costs = CostCalculator.calculate_cost(
        input_tokens=1_000_000,
        output_tokens=500_000,
        cache_write_tokens=50_000,
        cache_read_tokens=100_000,
        pricing=pricing,
    )
    assert token_repo.calls[0]["estimated_cost_usd"] == expected_costs.total_cost
    assert token_repo.calls[0]["input_cost_usd"] == expected_costs.input_cost
    assert token_repo.calls[0]["output_cost_usd"] == expected_costs.output_cost


@pytest.mark.asyncio
async def test_plan_pricing_snapshot_stored(monkeypatch: pytest.MonkeyPatch) -> None:
    pricing = ModelPricing(
        model_id="claude-haiku-4-5",
        region="global",
        input_price_per_million=Decimal("1.10"),
        output_price_per_million=Decimal("4.40"),
        cache_write_price_per_million=Decimal("1.30"),
        cache_read_price_per_million=Decimal("0.12"),
        effective_date=date(2025, 2, 1),
    )
    monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

    token_repo = FakeTokenUsageRepository()
    agg_repo = FakeUsageAggregateRepository()
    recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

    ctx = RequestContext(
        request_id="req-plan-snapshot",
        user_id=uuid4(),
        access_key_id=uuid4(),
        access_key_prefix="ak_plan",
        bedrock_region="ap-northeast-2",
        bedrock_model="claude-haiku-4-5",
        has_bedrock_key=True,
    )
    usage = AnthropicUsage(input_tokens=10, output_tokens=5)
    response = ProxyResponse(
        success=True,
        response=None,
        usage=usage,
        provider="plan",
        is_fallback=False,
        status_code=200,
    )

    await recorder._record_usage_with_cost(
        ctx, response, latency_ms=55, model="claude-haiku-4-5", provider="plan"
    )

    call = token_repo.calls[0]
    assert call["pricing_region"] == "global"
    assert call["pricing_model_id"] == "claude-haiku-4-5"
    assert call["pricing_effective_date"] == date(2025, 2, 1)
    assert call["pricing_input_price_per_million"] == Decimal("1.10")
    assert call["pricing_output_price_per_million"] == Decimal("4.40")
    assert call["pricing_cache_write_price_per_million"] == Decimal("1.30")
    assert call["pricing_cache_read_price_per_million"] == Decimal("0.12")
