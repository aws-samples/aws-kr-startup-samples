"""Tests for UsageRecorder.record() integration flow.

These tests verify the complete flow from record() through _record_usage_with_cost(),
including cost calculation, repository calls, and error handling.
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.domain import AnthropicUsage
from src.domain.pricing import ModelPricing, PricingConfig
from src.domain.cost_calculator import CostCalculator
from src.proxy.context import RequestContext
from src.proxy.router import ProxyResponse
from src.proxy.usage import UsageRecorder, _get_bucket_start
from src.proxy import usage as usage_module


@dataclass
class DummyMetricsEmitter:
    """Fake metrics emitter for testing."""

    calls: list = None

    def __post_init__(self):
        self.calls = []

    async def emit(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


class FakeTokenUsageRepository:
    """Fake token usage repository for testing."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.should_raise: Exception | None = None

    async def create(self, **kwargs):
        if self.should_raise:
            raise self.should_raise
        self.calls.append(kwargs)
        return kwargs


class FakeUsageAggregateRepository:
    """Fake usage aggregate repository for testing."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.should_raise: Exception | None = None

    async def increment(self, **kwargs) -> None:
        if self.should_raise:
            raise self.should_raise
        self.calls.append(kwargs)


class DummySession:
    def __init__(self) -> None:
        self.commit_called = False
        self.rollback_called = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False

    async def commit(self) -> None:
        self.commit_called = True

    async def rollback(self) -> None:
        self.rollback_called = True


def _capture_task_names(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    task_names: list[str] = []

    def _fake_create_task(coro):
        task_names.append(getattr(getattr(coro, "cr_code", None), "co_name", type(coro).__name__))
        if hasattr(coro, "close"):
            coro.close()
        return None

    monkeypatch.setattr(usage_module.asyncio, "create_task", _fake_create_task)
    return task_names


class TestRecordMethodFlow:
    """Test the record() method's conditional flow."""

    @pytest.mark.asyncio
    async def test_record_records_plan_usage(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify record() writes to DB for plan responses."""
        task_names = _capture_task_names(monkeypatch)
        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        ctx = RequestContext(
            request_id="req-1",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak_test",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )
        response = ProxyResponse(
            success=True,
            response=None,
            usage=AnthropicUsage(input_tokens=100, output_tokens=50),
            provider="plan",  # Not bedrock
            is_fallback=False,
            status_code=200,
        )

        await recorder.record(ctx, response, latency_ms=100, model=ctx.bedrock_model)

        assert task_names == ["emit"]
        assert len(token_repo.calls) == 1
        assert len(agg_repo.calls) == 5

    @pytest.mark.asyncio
    async def test_record_skips_db_for_failed_responses(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify record() does not write to DB for failed responses."""
        task_names = _capture_task_names(monkeypatch)
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
        response = ProxyResponse(
            success=False,  # Failed
            response=None,
            usage=None,
            provider="bedrock",
            is_fallback=False,
            status_code=500,
        )

        await recorder.record(ctx, response, latency_ms=100, model=ctx.bedrock_model)

        assert task_names == ["emit"]
        assert len(token_repo.calls) == 0
        assert len(agg_repo.calls) == 0

    @pytest.mark.asyncio
    async def test_record_skips_db_when_no_usage_data(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify record() does not write to DB when usage is None."""
        task_names = _capture_task_names(monkeypatch)
        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        ctx = RequestContext(
            request_id="req-3",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak_test",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )
        response = ProxyResponse(
            success=True,
            response=None,
            usage=None,  # No usage data
            provider="bedrock",
            is_fallback=False,
            status_code=200,
        )

        await recorder.record(ctx, response, latency_ms=100, model=ctx.bedrock_model)

        assert task_names == ["emit"]
        assert len(token_repo.calls) == 0
        assert len(agg_repo.calls) == 0

    @pytest.mark.asyncio
    async def test_record_schedules_metrics_and_calls_usage_recording(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify record() emits metrics (via create_task) and records usage (via shield).

        Note: _record_usage_with_cost is called via asyncio.shield() (not create_task),
        so we verify it was called by checking the repository calls directly.
        """
        task_names = _capture_task_names(monkeypatch)
        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        ctx = RequestContext(
            request_id="req-4",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak_test",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )
        response = ProxyResponse(
            success=True,
            response=None,
            usage=AnthropicUsage(input_tokens=100, output_tokens=50),
            provider="bedrock",
            is_fallback=False,
            status_code=200,
        )

        await recorder.record(ctx, response, latency_ms=100, model=ctx.bedrock_model)

        # Metrics emit is scheduled via create_task
        assert "emit" in task_names

        # _record_usage_with_cost is called via asyncio.shield() (awaited directly)
        # Verify it was called by checking the repository was used
        assert len(token_repo.calls) == 1
        assert len(agg_repo.calls) == 5  # 5 bucket types


class TestRecordUsageWithCostFlow:
    """Test the complete _record_usage_with_cost flow."""

    @pytest.mark.asyncio
    async def test_full_flow_creates_token_usage_and_aggregates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify complete flow creates token usage and all 5 bucket aggregates."""
        pricing = ModelPricing(
            model_id="claude-sonnet-4-5",
            region="ap-northeast-2",
            input_price_per_million=Decimal("3.00"),
            output_price_per_million=Decimal("15.00"),
            cache_write_price_per_million=Decimal("3.75"),
            cache_read_price_per_million=Decimal("0.30"),
            effective_date=date(2025, 1, 1),
        )
        monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        ctx = RequestContext(
            request_id="req-full",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak_test",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )
        usage = AnthropicUsage(
            input_tokens=1000,
            output_tokens=500,
            cache_read_input_tokens=100,
            cache_creation_input_tokens=50,
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
            latency_ms=150,
            model=ctx.bedrock_model,
            provider="bedrock",
        )

        # Verify token usage was created
        assert len(token_repo.calls) == 1
        token_call = token_repo.calls[0]
        assert token_call["input_tokens"] == 1000
        assert token_call["output_tokens"] == 500
        assert token_call["total_tokens"] == 1500
        assert token_call["pricing_model_id"] == "claude-sonnet-4-5"

        # Verify all 5 bucket types were incremented
        assert len(agg_repo.calls) == 5
        bucket_types = {call["bucket_type"] for call in agg_repo.calls}
        assert bucket_types == {"minute", "hour", "day", "week", "month"}

        # Verify each aggregate has correct values
        for agg_call in agg_repo.calls:
            assert agg_call["input_tokens"] == 1000
            assert agg_call["output_tokens"] == 500
            assert agg_call["total_tokens"] == 1500
            assert agg_call["cache_write_tokens"] == 50
            assert agg_call["cache_read_tokens"] == 100

    @pytest.mark.asyncio
    async def test_handles_none_cache_tokens(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify None cache tokens are treated as 0."""
        pricing = ModelPricing(
            model_id="claude-sonnet-4-5",
            region="ap-northeast-2",
            input_price_per_million=Decimal("3.00"),
            output_price_per_million=Decimal("15.00"),
            cache_write_price_per_million=Decimal("3.75"),
            cache_read_price_per_million=Decimal("0.30"),
            effective_date=date(2025, 1, 1),
        )
        monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        ctx = RequestContext(
            request_id="req-nocache",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak_test",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )
        usage = AnthropicUsage(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=None,  # None
            cache_creation_input_tokens=None,  # None
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
            latency_ms=50,
            model=ctx.bedrock_model,
            provider="bedrock",
        )

        # Cache tokens should be 0
        for agg_call in agg_repo.calls:
            assert agg_call["cache_write_tokens"] == 0
            assert agg_call["cache_read_tokens"] == 0


class TestSessionFactoryFlow:
    """Test session factory commit/rollback behavior."""

    @pytest.mark.asyncio
    async def test_commits_session_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pricing = ModelPricing(
            model_id="claude-sonnet-4-5",
            region="ap-northeast-2",
            input_price_per_million=Decimal("3.00"),
            output_price_per_million=Decimal("15.00"),
            cache_write_price_per_million=Decimal("3.75"),
            cache_read_price_per_million=Decimal("0.30"),
            effective_date=date(2025, 1, 1),
        )
        monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

        sessions: list[DummySession] = []

        def session_factory():
            session = DummySession()
            sessions.append(session)
            return session

        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(
            token_repo,
            agg_repo,
            metrics_emitter=DummyMetricsEmitter(),
            session_factory=session_factory,
        )
        monkeypatch.setattr(recorder, "_persist_usage", AsyncMock())

        ctx = RequestContext(
            request_id="req-session-1",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak_test",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )
        usage = AnthropicUsage(input_tokens=100, output_tokens=50)
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
            latency_ms=50,
            model=ctx.bedrock_model,
            provider="bedrock",
        )

        assert sessions[0].commit_called is True
        assert sessions[0].rollback_called is False
        recorder._persist_usage.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rolls_back_session_on_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pricing = ModelPricing(
            model_id="claude-sonnet-4-5",
            region="ap-northeast-2",
            input_price_per_million=Decimal("3.00"),
            output_price_per_million=Decimal("15.00"),
            cache_write_price_per_million=Decimal("3.75"),
            cache_read_price_per_million=Decimal("0.30"),
            effective_date=date(2025, 1, 1),
        )
        monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

        sessions: list[DummySession] = []

        def session_factory():
            session = DummySession()
            sessions.append(session)
            return session

        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(
            token_repo,
            agg_repo,
            metrics_emitter=DummyMetricsEmitter(),
            session_factory=session_factory,
        )
        monkeypatch.setattr(recorder, "_persist_usage", AsyncMock(side_effect=RuntimeError("fail")))

        ctx = RequestContext(
            request_id="req-session-2",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak_test",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )
        usage = AnthropicUsage(input_tokens=100, output_tokens=50)
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
            latency_ms=50,
            model=ctx.bedrock_model,
            provider="bedrock",
        )

        assert sessions[0].rollback_called is True
        assert sessions[0].commit_called is False


class TestCalculateCostSafe:
    """Test _calculate_cost_safe error handling."""

    def test_returns_zero_cost_when_pricing_not_found(self) -> None:
        """Verify zero cost returned when no pricing found."""
        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        with patch.object(PricingConfig, "get_pricing", return_value=None):
            cost, pricing = recorder._calculate_cost_safe(
                model="unknown-model",
                region="ap-northeast-2",
                provider="bedrock",
                input_tokens=100,
                output_tokens=50,
                cache_write_tokens=10,
                cache_read_tokens=5,
            )

        assert pricing is None
        assert cost.total_cost == Decimal("0.000000")
        assert cost.input_cost == Decimal("0.000000")
        assert cost.output_cost == Decimal("0.000000")

    def test_returns_zero_cost_on_pricing_exception(self) -> None:
        """Verify zero cost returned when pricing lookup raises exception."""
        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        def raise_error(*args, **kwargs):
            raise RuntimeError("pricing service unavailable")

        with patch.object(PricingConfig, "get_pricing", side_effect=raise_error):
            cost, pricing = recorder._calculate_cost_safe(
                model="claude-sonnet-4-5",
                region="ap-northeast-2",
                provider="bedrock",
                input_tokens=100,
                output_tokens=50,
                cache_write_tokens=10,
                cache_read_tokens=5,
            )

        assert pricing is None
        assert cost.total_cost == Decimal("0.000000")

    def test_returns_calculated_cost_when_pricing_found(self) -> None:
        """Verify correct cost returned when pricing is available."""
        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        pricing = ModelPricing(
            model_id="claude-opus-4-5",
            region="ap-northeast-2",
            input_price_per_million=Decimal("5.00"),
            output_price_per_million=Decimal("25.00"),
            cache_write_price_per_million=Decimal("6.25"),
            cache_read_price_per_million=Decimal("0.50"),
            effective_date=date(2025, 1, 1),
        )

        with patch.object(PricingConfig, "get_pricing", return_value=pricing):
            cost, returned_pricing = recorder._calculate_cost_safe(
                model="anthropic.claude-opus-4-5-20250514",
                region="ap-northeast-2",
                provider="bedrock",
                input_tokens=1_000_000,
                output_tokens=500_000,
                cache_write_tokens=100_000,
                cache_read_tokens=200_000,
            )

        assert returned_pricing == pricing
        assert cost.input_cost == Decimal("5.000000")
        assert cost.output_cost == Decimal("12.500000")
        assert cost.cache_write_cost == Decimal("0.625000")
        assert cost.cache_read_cost == Decimal("0.100000")
        assert cost.total_cost == Decimal("18.225000")


class TestErrorRecovery:
    """Test error handling and recovery in usage recording."""

    @pytest.mark.asyncio
    async def test_continues_on_token_repo_error(
        self, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """Verify errors in token repo are logged but don't crash."""
        pricing = ModelPricing(
            model_id="claude-sonnet-4-5",
            region="ap-northeast-2",
            input_price_per_million=Decimal("3.00"),
            output_price_per_million=Decimal("15.00"),
            cache_write_price_per_million=Decimal("3.75"),
            cache_read_price_per_million=Decimal("0.30"),
            effective_date=date(2025, 1, 1),
        )
        monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

        token_repo = FakeTokenUsageRepository()
        token_repo.should_raise = RuntimeError("DB connection failed")
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        ctx = RequestContext(
            request_id="req-error",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak_test",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )
        usage = AnthropicUsage(input_tokens=100, output_tokens=50)
        response = ProxyResponse(
            success=True,
            response=None,
            usage=usage,
            provider="bedrock",
            is_fallback=False,
            status_code=200,
        )

        # Should not raise
        await recorder._record_usage_with_cost(
            ctx,
            response,
            latency_ms=50,
            model=ctx.bedrock_model,
            provider="bedrock",
        )

        # Aggregate calls should not have been made due to early failure
        assert len(agg_repo.calls) == 0


class TestBucketStartCalculation:
    """Test bucket_start calculation for different bucket types."""

    @pytest.mark.asyncio
    async def test_all_bucket_starts_have_timezone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify all bucket_start values are timezone-aware UTC."""
        pricing = ModelPricing(
            model_id="claude-sonnet-4-5",
            region="ap-northeast-2",
            input_price_per_million=Decimal("3.00"),
            output_price_per_million=Decimal("15.00"),
            cache_write_price_per_million=Decimal("3.75"),
            cache_read_price_per_million=Decimal("0.30"),
            effective_date=date(2025, 1, 1),
        )
        monkeypatch.setattr(PricingConfig, "get_pricing", lambda *_args, **_kwargs: pricing)

        token_repo = FakeTokenUsageRepository()
        agg_repo = FakeUsageAggregateRepository()
        recorder = UsageRecorder(token_repo, agg_repo, metrics_emitter=DummyMetricsEmitter())

        ctx = RequestContext(
            request_id="req-tz",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak_test",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )
        usage = AnthropicUsage(input_tokens=100, output_tokens=50)
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
            latency_ms=50,
            model=ctx.bedrock_model,
            provider="bedrock",
        )

        # All bucket_start values should be timezone-aware
        for agg_call in agg_repo.calls:
            assert agg_call["bucket_start"].tzinfo is not None
