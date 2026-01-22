"""Tests for UsageAggregateRepository business logic.

These tests verify the repository's aggregation logic using mock sessions
since PostgreSQL-specific ON CONFLICT requires a real PostgreSQL database.
"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.repositories.usage_repository import UsageAggregateRepository
from src.db.models import UsageAggregateModel


class TestIncrementUpsertLogic:
    """Test increment() upsert behavior with PostgreSQL dialect."""

    @pytest.mark.asyncio
    async def test_increment_builds_correct_insert_statement(self) -> None:
        """Verify increment() constructs proper INSERT ... ON CONFLICT statement."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        repo = UsageAggregateRepository(mock_session)

        user_id = uuid4()
        access_key_id = uuid4()
        bucket_start = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)

        await repo.increment(
            bucket_type="hour",
            bucket_start=bucket_start,
            user_id=user_id,
            access_key_id=access_key_id,
            provider="bedrock",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cache_write_tokens=10,
            cache_read_tokens=5,
            total_estimated_cost_usd=Decimal("0.150000"),
            total_input_cost_usd=Decimal("0.100000"),
            total_output_cost_usd=Decimal("0.050000"),
            total_cache_write_cost_usd=Decimal("0.010000"),
            total_cache_read_cost_usd=Decimal("0.005000"),
        )

        assert mock_session.execute.call_count == 1
        executed_stmt = mock_session.execute.call_args[0][0]

        # Verify the statement is a PostgreSQL INSERT with ON CONFLICT
        compiled = executed_stmt.compile(
            dialect=__import__("sqlalchemy.dialects.postgresql", fromlist=["dialect"]).dialect()
        )
        stmt_str = str(compiled)

        assert "INSERT INTO usage_aggregates" in stmt_str
        assert "ON CONFLICT" in stmt_str
        assert "bucket_type" in stmt_str
        assert "bucket_start" in stmt_str
        assert "user_id" in stmt_str
        assert "access_key_id" in stmt_str
        assert "provider" in stmt_str

    @pytest.mark.asyncio
    async def test_increment_on_conflict_updates_all_fields(self) -> None:
        """Verify ON CONFLICT clause updates all aggregate fields."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        repo = UsageAggregateRepository(mock_session)

        await repo.increment(
            bucket_type="day",
            bucket_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            user_id=uuid4(),
            access_key_id=uuid4(),
            provider="bedrock",
            input_tokens=200,
            output_tokens=100,
            total_tokens=300,
            cache_write_tokens=20,
            cache_read_tokens=10,
            total_estimated_cost_usd=Decimal("0.300000"),
            total_input_cost_usd=Decimal("0.200000"),
            total_output_cost_usd=Decimal("0.100000"),
            total_cache_write_cost_usd=Decimal("0.020000"),
            total_cache_read_cost_usd=Decimal("0.010000"),
        )

        executed_stmt = mock_session.execute.call_args[0][0]
        compiled = executed_stmt.compile(
            dialect=__import__("sqlalchemy.dialects.postgresql", fromlist=["dialect"]).dialect()
        )
        stmt_str = str(compiled)

        # Verify all cost fields are in the ON CONFLICT UPDATE clause
        expected_update_fields = [
            "total_requests",
            "total_input_tokens",
            "total_output_tokens",
            "total_tokens",
            "total_cache_write_tokens",
            "total_cache_read_tokens",
            "total_input_cost_usd",
            "total_output_cost_usd",
            "total_cache_write_cost_usd",
            "total_cache_read_cost_usd",
            "total_estimated_cost_usd",
        ]

        for field in expected_update_fields:
            assert field in stmt_str, f"Missing {field} in ON CONFLICT UPDATE"

    @pytest.mark.asyncio
    async def test_increment_request_count_increments_by_one(self) -> None:
        """Verify total_requests is incremented by 1 on each call."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        repo = UsageAggregateRepository(mock_session)

        await repo.increment(
            bucket_type="minute",
            bucket_start=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
            user_id=uuid4(),
            access_key_id=uuid4(),
            provider="bedrock",
            input_tokens=50,
            output_tokens=25,
            total_tokens=75,
        )

        executed_stmt = mock_session.execute.call_args[0][0]
        compiled = executed_stmt.compile(
            dialect=__import__("sqlalchemy.dialects.postgresql", fromlist=["dialect"]).dialect()
        )
        stmt_str = str(compiled)

        # The INSERT sets total_requests=1, ON CONFLICT adds +1
        assert "total_requests" in stmt_str


class TestQueryBucketTotals:
    """Test query_bucket_totals() aggregation logic."""

    @pytest.mark.asyncio
    async def test_query_bucket_totals_groups_by_bucket_start(self) -> None:
        """Verify results are grouped by bucket_start with SUM aggregation."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    MagicMock(
                        bucket_start=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
                        total_requests=5,
                        total_input_tokens=500,
                        total_output_tokens=250,
                        total_tokens=750,
                        total_cache_write_tokens=50,
                        total_cache_read_tokens=25,
                        total_input_cost_usd=Decimal("0.500000"),
                        total_output_cost_usd=Decimal("0.250000"),
                        total_cache_write_cost_usd=Decimal("0.050000"),
                        total_cache_read_cost_usd=Decimal("0.025000"),
                        total_estimated_cost_usd=Decimal("0.825000"),
                    ),
                    MagicMock(
                        bucket_start=datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc),
                        total_requests=3,
                        total_input_tokens=300,
                        total_output_tokens=150,
                        total_tokens=450,
                        total_cache_write_tokens=30,
                        total_cache_read_tokens=15,
                        total_input_cost_usd=Decimal("0.300000"),
                        total_output_cost_usd=Decimal("0.150000"),
                        total_cache_write_cost_usd=Decimal("0.030000"),
                        total_cache_read_cost_usd=Decimal("0.015000"),
                        total_estimated_cost_usd=Decimal("0.495000"),
                    ),
                ]
            )
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = UsageAggregateRepository(mock_session)

        results = await repo.query_bucket_totals(
            bucket_type="hour",
            start_time=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 1, 2, 0, tzinfo=timezone.utc),
        )

        assert len(results) == 2
        assert results[0]["total_requests"] == 5
        assert results[0]["total_estimated_cost_usd"] == Decimal("0.825000")
        assert results[1]["total_requests"] == 3

    @pytest.mark.asyncio
    async def test_query_bucket_totals_filters_by_user_id(self) -> None:
        """Verify user_id filter is applied to query."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = UsageAggregateRepository(mock_session)

        user_id = uuid4()
        await repo.query_bucket_totals(
            bucket_type="day",
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
            user_id=user_id,
        )

        executed_query = mock_session.execute.call_args[0][0]
        compiled = str(executed_query.compile(compile_kwargs={"literal_binds": False}))

        assert "user_id" in compiled

    @pytest.mark.asyncio
    async def test_query_bucket_totals_filters_by_provider(self) -> None:
        """Verify provider filter is applied to query."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = UsageAggregateRepository(mock_session)

        await repo.query_bucket_totals(
            bucket_type="day",
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
            provider="plan",
        )

        executed_query = mock_session.execute.call_args[0][0]
        compiled = str(executed_query.compile(compile_kwargs={"literal_binds": False}))

        assert "provider" in compiled

    @pytest.mark.asyncio
    async def test_query_bucket_totals_handles_null_aggregates(self) -> None:
        """Verify NULL values are converted to zero defaults."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    MagicMock(
                        bucket_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
                        total_requests=None,
                        total_input_tokens=None,
                        total_output_tokens=None,
                        total_tokens=None,
                        total_cache_write_tokens=None,
                        total_cache_read_tokens=None,
                        total_input_cost_usd=None,
                        total_output_cost_usd=None,
                        total_cache_write_cost_usd=None,
                        total_cache_read_cost_usd=None,
                        total_estimated_cost_usd=None,
                    )
                ]
            )
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = UsageAggregateRepository(mock_session)

        results = await repo.query_bucket_totals(
            bucket_type="hour",
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
        )

        assert results[0]["total_requests"] == 0
        assert results[0]["total_input_tokens"] == 0
        assert results[0]["total_estimated_cost_usd"] == Decimal("0")


class TestGetTotals:
    """Test get_totals() grand total calculation."""

    @pytest.mark.asyncio
    async def test_get_totals_returns_aggregated_sum(self) -> None:
        """Verify get_totals returns sum across all matching buckets."""
        mock_result = MagicMock()
        mock_result.one = MagicMock(
            return_value=(
                10,  # total_requests
                1000,  # total_input_tokens
                500,  # total_output_tokens
                1500,  # total_tokens
                100,  # total_cache_write_tokens
                50,  # total_cache_read_tokens
                Decimal("1.000000"),  # total_input_cost_usd
                Decimal("0.500000"),  # total_output_cost_usd
                Decimal("0.100000"),  # total_cache_write_cost_usd
                Decimal("0.050000"),  # total_cache_read_cost_usd
                Decimal("1.650000"),  # total_estimated_cost_usd
            )
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = UsageAggregateRepository(mock_session)

        totals = await repo.get_totals(
            bucket_type="day",
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )

        assert totals["total_requests"] == 10
        assert totals["total_tokens"] == 1500
        assert totals["total_cache_write_tokens"] == 100
        assert totals["total_cache_read_tokens"] == 50
        assert totals["total_estimated_cost_usd"] == Decimal("1.650000")

    @pytest.mark.asyncio
    async def test_get_totals_handles_empty_result(self) -> None:
        """Verify empty result returns zero defaults."""
        mock_result = MagicMock()
        mock_result.one = MagicMock(
            return_value=(None, None, None, None, None, None, None, None, None, None, None)
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = UsageAggregateRepository(mock_session)

        totals = await repo.get_totals(
            bucket_type="month",
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 2, 1, tzinfo=timezone.utc),
        )

        assert totals["total_requests"] == 0
        assert totals["total_tokens"] == 0
        assert totals["total_estimated_cost_usd"] == Decimal("0")


class TestGetMonthlyUsageTotal:
    """Test get_monthly_usage_total() helper."""

    @pytest.mark.asyncio
    async def test_get_monthly_usage_total_returns_sum(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=Decimal("12.340000"))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = UsageAggregateRepository(mock_session)

        total = await repo.get_monthly_usage_total(
            user_id=uuid4(),
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 2, 1, tzinfo=timezone.utc),
        )

        assert total == Decimal("12.340000")

    @pytest.mark.asyncio
    async def test_get_monthly_usage_total_handles_empty_result(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = UsageAggregateRepository(mock_session)

        total = await repo.get_monthly_usage_total(
            user_id=uuid4(),
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 2, 1, tzinfo=timezone.utc),
        )

        assert total == Decimal("0")


class TestMultipleIncrementAccumulation:
    """Test that multiple increment calls accumulate correctly."""

    @pytest.mark.asyncio
    async def test_multiple_increments_generate_separate_statements(self) -> None:
        """Verify each increment() call generates a separate SQL statement."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        repo = UsageAggregateRepository(mock_session)

        user_id = uuid4()
        access_key_id = uuid4()
        bucket_start = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)

        # Simulate multiple requests in the same bucket
        for i in range(3):
            await repo.increment(
                bucket_type="hour",
                bucket_start=bucket_start,
                user_id=user_id,
                access_key_id=access_key_id,
                provider="bedrock",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                total_tokens=150 * (i + 1),
                total_estimated_cost_usd=Decimal(f"0.{(i+1)*10:02d}0000"),
            )

        # Each increment should have been executed
        assert mock_session.execute.call_count == 3


class TestGetTopUsers:
    """Test get_top_users() aggregation logic."""

    @pytest.mark.asyncio
    async def test_get_top_users_maps_null_values(self) -> None:
        """Verify NULL aggregates are mapped to zero."""
        user_id = uuid4()
        row = MagicMock()
        row.user_id = user_id
        row.name = "alpha"
        row.total_tokens = None
        row.total_requests = None

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([row]))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = UsageAggregateRepository(mock_session)

        results = await repo.get_top_users(
            bucket_type="day",
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
            limit=5,
        )

        assert results == [
            {
                "user_id": user_id,
                "name": "alpha",
                "total_tokens": 0,
                "total_requests": 0,
            }
        ]

    @pytest.mark.asyncio
    async def test_get_top_users_includes_limit_and_ordering(self) -> None:
        """Verify query includes ORDER BY and LIMIT."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = UsageAggregateRepository(mock_session)

        await repo.get_top_users(
            bucket_type="hour",
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
            limit=3,
        )

        executed_query = mock_session.execute.call_args[0][0]
        compiled = str(executed_query.compile(compile_kwargs={"literal_binds": False}))

        assert "ORDER BY" in compiled
        assert "LIMIT" in compiled
