from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.api import admin_usage
from src.domain import UsageResponse


class FakeUsageAggregateRepository:
    last_call: dict | None = None

    def __init__(self, _session) -> None:
        return None

    async def query_bucket_totals(self, **kwargs):
        FakeUsageAggregateRepository.last_call = kwargs
        return [
            {
                "bucket_start": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "total_requests": 2,
                "total_input_tokens": 100,
                "total_output_tokens": 50,
                "total_tokens": 150,
                "total_cache_write_tokens": 5,
                "total_cache_read_tokens": 3,
                "total_input_cost_usd": Decimal("0.100000"),
                "total_output_cost_usd": Decimal("0.050000"),
                "total_cache_write_cost_usd": Decimal("0.010000"),
                "total_cache_read_cost_usd": Decimal("0.005000"),
                "total_estimated_cost_usd": Decimal("0.165000"),
            }
        ]

    async def get_totals(self, **kwargs):
        FakeUsageAggregateRepository.last_call = kwargs
        return {
            "total_requests": 2,
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "total_tokens": 150,
            "total_cache_write_tokens": 5,
            "total_cache_read_tokens": 3,
            "total_input_cost_usd": Decimal("0.100000"),
            "total_output_cost_usd": Decimal("0.050000"),
            "total_cache_write_cost_usd": Decimal("0.010000"),
            "total_cache_read_cost_usd": Decimal("0.005000"),
            "total_estimated_cost_usd": Decimal("0.165000"),
        }


class FakeTokenUsageRepository:
    last_call: dict | None = None

    def __init__(self, _session) -> None:
        return None

    async def get_cost_breakdown_by_model(self, **kwargs):
        FakeTokenUsageRepository.last_call = kwargs
        return [
            {
                "pricing_model_id": "claude-opus-4-5",
                "input_cost_usd": Decimal("0.100000"),
                "output_cost_usd": Decimal("0.050000"),
                "cache_write_cost_usd": Decimal("0.010000"),
                "cache_read_cost_usd": Decimal("0.005000"),
                "total_cost_usd": Decimal("0.165000"),
            }
        ]


# Feature: cost-visibility, Property 5: Usage Summary API Response Completeness
@pytest.mark.asyncio
async def test_get_usage_response_includes_costs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_usage, "UsageAggregateRepository", FakeUsageAggregateRepository)
    monkeypatch.setattr(admin_usage, "TokenUsageRepository", FakeTokenUsageRepository)

    response = await admin_usage.get_usage(
        user_id=uuid4(),
        team_id=None,
        access_key_id=None,
        bucket_type="day",
        provider=None,
        period=None,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 1),
        session=None,
    )

    assert isinstance(response, UsageResponse)
    assert response.total_cache_write_tokens == 5
    assert response.total_cache_read_tokens == 3
    assert response.total_input_cost_usd == "0.100000"
    assert response.total_output_cost_usd == "0.050000"
    assert response.estimated_cost_usd == "0.165000"
    assert response.cost_breakdown[0].model_id == "claude-opus-4-5"
    assert response.cost_breakdown[0].total_cost_usd == "0.165000"


@pytest.mark.asyncio
async def test_get_usage_filters_by_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_usage, "UsageAggregateRepository", FakeUsageAggregateRepository)
    monkeypatch.setattr(admin_usage, "TokenUsageRepository", FakeTokenUsageRepository)

    await admin_usage.get_usage(
        user_id=uuid4(),
        team_id=None,
        access_key_id=None,
        bucket_type="day",
        provider="plan",
        period=None,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 1),
        session=None,
    )

    assert FakeUsageAggregateRepository.last_call is not None
    assert FakeUsageAggregateRepository.last_call["provider"] == "plan"
    assert FakeTokenUsageRepository.last_call is not None
    assert FakeTokenUsageRepository.last_call["provider"] == "plan"


# Feature: cost-visibility, Property 10: KST Bucket Boundaries

def test_resolve_time_range_week_starts_sunday_kst() -> None:
    now_utc = datetime(2025, 1, 6, 3, 0, tzinfo=timezone.utc)  # Monday noon KST

    start_utc, end_utc = admin_usage._resolve_time_range(
        period="week",
        start_date=None,
        end_date=None,
        now_utc=now_utc,
    )

    assert start_utc == datetime(2025, 1, 4, 15, 0, tzinfo=timezone.utc)
    assert end_utc == now_utc


class FakeTopUsersRepository:
    last_call: dict | None = None

    def __init__(self, _session) -> None:
        return None

    async def get_top_users(self, **kwargs):
        FakeTopUsersRepository.last_call = kwargs
        return [
            {
                "user_id": uuid4(),
                "name": "alpha",
                "total_tokens": 1200,
                "total_requests": 12,
            }
        ]


@pytest.mark.asyncio
async def test_get_top_users_defaults_to_last_24_hours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_now = datetime(2025, 1, 2, 3, 4, 5)

    class FixedDateTime:
        @classmethod
        def utcnow(cls):
            return fixed_now

    monkeypatch.setattr(admin_usage, "UsageAggregateRepository", FakeTopUsersRepository)
    monkeypatch.setattr(admin_usage, "datetime", FixedDateTime)

    await admin_usage.get_top_users(bucket_type="hour", provider=None, session=None)

    assert FakeTopUsersRepository.last_call is not None
    assert FakeTopUsersRepository.last_call["end_time"] == fixed_now
    assert FakeTopUsersRepository.last_call["start_time"] == fixed_now - timedelta(hours=24)
    assert FakeTopUsersRepository.last_call["bucket_type"] == "hour"
    assert FakeTopUsersRepository.last_call["limit"] == 10


@pytest.mark.asyncio
async def test_get_top_users_maps_results(monkeypatch: pytest.MonkeyPatch) -> None:
    class ResultRepo:
        def __init__(self, _session) -> None:
            return None

        async def get_top_users(self, **_kwargs):
            return [
                {
                    "user_id": uuid4(),
                    "name": "bravo",
                    "total_tokens": 450,
                    "total_requests": 3,
                }
            ]

    monkeypatch.setattr(admin_usage, "UsageAggregateRepository", ResultRepo)

    start = datetime(2025, 1, 1, 0, 0)
    end = datetime(2025, 1, 2, 0, 0)
    results = await admin_usage.get_top_users(
        bucket_type="day",
        provider="bedrock",
        start_time=start,
        end_time=end,
        limit=5,
        session=None,
    )

    assert results[0].name == "bravo"
    assert results[0].total_tokens == 450
    assert results[0].total_requests == 3


@pytest.mark.asyncio
async def test_get_top_user_series_filters_by_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SeriesRepo:
        calls: dict[str, dict] = {}

        def __init__(self, _session) -> None:
            return None

        async def get_top_users(self, **kwargs):
            SeriesRepo.calls["top_users"] = kwargs
            return [
                {
                    "user_id": uuid4(),
                    "name": "alpha",
                    "total_tokens": 200,
                    "total_requests": 2,
                }
            ]

        async def get_user_series(self, **kwargs):
            SeriesRepo.calls["series"] = kwargs
            return []

    monkeypatch.setattr(admin_usage, "UsageAggregateRepository", SeriesRepo)

    start = datetime(2025, 1, 1, 0, 0)
    end = datetime(2025, 1, 2, 0, 0)
    await admin_usage.get_top_user_series(
        bucket_type="day",
        provider="plan",
        start_time=start,
        end_time=end,
        limit=1,
        session=None,
    )

    assert SeriesRepo.calls["top_users"]["provider"] == "plan"
    assert SeriesRepo.calls["series"]["provider"] == "plan"
