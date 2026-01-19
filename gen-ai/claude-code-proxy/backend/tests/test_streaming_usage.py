from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.domain import AnthropicUsage
from src.domain.pricing import ModelPricing, PricingConfig
from src.proxy.context import RequestContext
from src.proxy.streaming_usage import StreamingUsageCollector
from src.proxy.usage import UsageRecorder


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
    async def emit(self, *_args, **_kwargs) -> None:  # pragma: no cover
        return None


def test_streaming_usage_collector_captures_usage() -> None:
    """Test usage collection from message_start + message_delta (Anthropic format)."""
    collector = StreamingUsageCollector()

    collector.feed(
        b'data: {"type":"message_start","message":{"usage":{"input_tokens":12}}}\n\n'
    )
    collector.feed(
        b'data: {"type":"message_delta","usage":{"output_tokens":5,"cache_read_input_tokens":2,"cache_creation_input_tokens":1}}\n\n'
    )

    usage = collector.get_usage()
    assert usage is not None
    assert usage.input_tokens == 12
    assert usage.output_tokens == 5
    assert usage.cache_read_input_tokens == 2
    assert usage.cache_creation_input_tokens == 1


def test_streaming_usage_collector_prefers_message_delta_input_tokens() -> None:
    """Test that input_tokens from message_delta is preferred over message_start.

    Bedrock Converse API provides input_tokens in message_delta, not message_start.
    """
    collector = StreamingUsageCollector()

    # message_start has input_tokens=0 (Bedrock's converted format)
    collector.feed(
        b'data: {"type":"message_start","message":{"usage":{"input_tokens":0,"output_tokens":0}}}\n\n'
    )
    # message_delta has the actual input_tokens from Bedrock metadata
    collector.feed(
        b'data: {"type":"message_delta","usage":{"input_tokens":100,"output_tokens":50,"cache_read_input_tokens":10}}\n\n'
    )

    usage = collector.get_usage()
    assert usage is not None
    assert usage.input_tokens == 100  # Should use message_delta's value, not message_start's 0
    assert usage.output_tokens == 50
    assert usage.cache_read_input_tokens == 10


def test_streaming_usage_collector_handles_event_lines_after_data() -> None:
    collector = StreamingUsageCollector()

    collector.feed(
        b"event: message_start\n"
        b'data: {"type":"message_start","message":{"usage":{"input_tokens":12}}}\n\n'
    )
    collector.feed(
        b"event: message_delta\n"
        b'data: {"type":"message_delta","usage":{"output_tokens":5,"cache_read_input_tokens":2,"cache_creation_input_tokens":1}}\n\n'
    )

    usage = collector.get_usage()
    assert usage is not None
    assert usage.input_tokens == 12
    assert usage.output_tokens == 5
    assert usage.cache_read_input_tokens == 2
    assert usage.cache_creation_input_tokens == 1


@pytest.mark.asyncio
async def test_record_streaming_usage_records_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    pricing = ModelPricing(
        model_id="claude-haiku-4-5",
        region="ap-northeast-2",
        input_price_per_million=Decimal("1.00"),
        output_price_per_million=Decimal("2.00"),
        cache_write_price_per_million=Decimal("3.00"),
        cache_read_price_per_million=Decimal("4.00"),
        effective_date=date(2025, 1, 1),
    )
    monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

    token_repo = FakeTokenUsageRepository()
    agg_repo = FakeUsageAggregateRepository()
    recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

    ctx = RequestContext(
        request_id="req-stream",
        user_id=uuid4(),
        access_key_id=uuid4(),
        access_key_prefix="ak",
        bedrock_region="ap-northeast-2",
        bedrock_model="anthropic.claude-haiku-4-5-20250514",
        has_bedrock_key=True,
    )
    usage = AnthropicUsage(
        input_tokens=10,
        output_tokens=5,
        cache_read_input_tokens=2,
        cache_creation_input_tokens=1,
    )

    await recorder.record_streaming_usage(
        ctx,
        usage,
        latency_ms=50,
        model=ctx.bedrock_model,
        is_fallback=True,
    )

    assert len(token_repo.calls) == 1
    assert len(agg_repo.calls) == 5
