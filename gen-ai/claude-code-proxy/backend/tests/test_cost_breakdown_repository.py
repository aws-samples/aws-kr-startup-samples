"""Tests for TokenUsageRepository.get_cost_breakdown_by_model().

These tests verify the cost breakdown aggregation query logic.
"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.repositories.usage_repository import TokenUsageRepository


class TestGetCostBreakdownByModel:
    """Test get_cost_breakdown_by_model() aggregation logic."""

    @pytest.mark.asyncio
    async def test_returns_grouped_costs_by_model(self) -> None:
        """Verify costs are grouped by pricing_model_id with correct sums."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    MagicMock(
                        pricing_model_id="claude-opus-4-5",
                        input_cost_usd=Decimal("1.000000"),
                        output_cost_usd=Decimal("2.500000"),
                        cache_write_cost_usd=Decimal("0.100000"),
                        cache_read_cost_usd=Decimal("0.050000"),
                        total_cost_usd=Decimal("3.650000"),
                    ),
                    MagicMock(
                        pricing_model_id="claude-sonnet-4-5",
                        input_cost_usd=Decimal("0.300000"),
                        output_cost_usd=Decimal("0.750000"),
                        cache_write_cost_usd=Decimal("0.030000"),
                        cache_read_cost_usd=Decimal("0.015000"),
                        total_cost_usd=Decimal("1.095000"),
                    ),
                ]
            )
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = TokenUsageRepository(mock_session)

        results = await repo.get_cost_breakdown_by_model(
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )

        assert len(results) == 2

        opus = results[0]
        assert opus["pricing_model_id"] == "claude-opus-4-5"
        assert opus["input_cost_usd"] == Decimal("1.000000")
        assert opus["output_cost_usd"] == Decimal("2.500000")
        assert opus["cache_write_cost_usd"] == Decimal("0.100000")
        assert opus["cache_read_cost_usd"] == Decimal("0.050000")
        assert opus["total_cost_usd"] == Decimal("3.650000")

        sonnet = results[1]
        assert sonnet["pricing_model_id"] == "claude-sonnet-4-5"
        assert sonnet["total_cost_usd"] == Decimal("1.095000")

    @pytest.mark.asyncio
    async def test_filters_by_time_range(self) -> None:
        """Verify query includes correct time range filter."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = TokenUsageRepository(mock_session)

        start = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, 0, 0, tzinfo=timezone.utc)

        await repo.get_cost_breakdown_by_model(start_time=start, end_time=end)

        executed_query = mock_session.execute.call_args[0][0]
        compiled = str(executed_query.compile(compile_kwargs={"literal_binds": False}))

        assert "timestamp >=" in compiled
        assert "timestamp <" in compiled

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self) -> None:
        """Verify user_id filter is applied when provided."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = TokenUsageRepository(mock_session)

        user_id = uuid4()

        await repo.get_cost_breakdown_by_model(
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
            user_id=user_id,
        )

        executed_query = mock_session.execute.call_args[0][0]
        compiled = str(executed_query.compile(compile_kwargs={"literal_binds": False}))

        # Query should include user_id filter
        assert "user_id" in compiled

    @pytest.mark.asyncio
    async def test_filters_by_access_key_id(self) -> None:
        """Verify access_key_id filter is applied when provided."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = TokenUsageRepository(mock_session)

        access_key_id = uuid4()

        await repo.get_cost_breakdown_by_model(
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
            access_key_id=access_key_id,
        )

        executed_query = mock_session.execute.call_args[0][0]
        compiled = str(executed_query.compile(compile_kwargs={"literal_binds": False}))

        # Query should include access_key_id filter
        assert "access_key_id" in compiled

    @pytest.mark.asyncio
    async def test_handles_null_cost_values(self) -> None:
        """Verify NULL cost values are converted to Decimal zero."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    MagicMock(
                        pricing_model_id="claude-haiku-4-5",
                        input_cost_usd=None,
                        output_cost_usd=None,
                        cache_write_cost_usd=None,
                        cache_read_cost_usd=None,
                        total_cost_usd=None,
                    )
                ]
            )
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = TokenUsageRepository(mock_session)

        results = await repo.get_cost_breakdown_by_model(
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
        )

        assert len(results) == 1
        assert results[0]["input_cost_usd"] == Decimal("0")
        assert results[0]["output_cost_usd"] == Decimal("0")
        assert results[0]["cache_write_cost_usd"] == Decimal("0")
        assert results[0]["cache_read_cost_usd"] == Decimal("0")
        assert results[0]["total_cost_usd"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_data(self) -> None:
        """Verify empty list is returned when no matching records exist."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = TokenUsageRepository(mock_session)

        results = await repo.get_cost_breakdown_by_model(
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_orders_by_model_id(self) -> None:
        """Verify results are ordered by pricing_model_id."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    MagicMock(
                        pricing_model_id="claude-haiku-4-5",
                        input_cost_usd=Decimal("0.1"),
                        output_cost_usd=Decimal("0.2"),
                        cache_write_cost_usd=Decimal("0.01"),
                        cache_read_cost_usd=Decimal("0.005"),
                        total_cost_usd=Decimal("0.315"),
                    ),
                    MagicMock(
                        pricing_model_id="claude-opus-4-5",
                        input_cost_usd=Decimal("1.0"),
                        output_cost_usd=Decimal("2.0"),
                        cache_write_cost_usd=Decimal("0.1"),
                        cache_read_cost_usd=Decimal("0.05"),
                        total_cost_usd=Decimal("3.15"),
                    ),
                    MagicMock(
                        pricing_model_id="claude-sonnet-4-5",
                        input_cost_usd=Decimal("0.5"),
                        output_cost_usd=Decimal("1.0"),
                        cache_write_cost_usd=Decimal("0.05"),
                        cache_read_cost_usd=Decimal("0.025"),
                        total_cost_usd=Decimal("1.575"),
                    ),
                ]
            )
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = TokenUsageRepository(mock_session)

        await repo.get_cost_breakdown_by_model(
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )

        executed_query = mock_session.execute.call_args[0][0]
        compiled = str(executed_query.compile(compile_kwargs={"literal_binds": False}))

        # Verify ORDER BY is in the query
        assert "ORDER BY" in compiled
        assert "pricing_model_id" in compiled


class TestCostBreakdownIntegration:
    """Integration-style tests for cost breakdown with both filters."""

    @pytest.mark.asyncio
    async def test_combined_filters_user_and_access_key(self) -> None:
        """Verify both user_id and access_key_id filters work together."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    MagicMock(
                        pricing_model_id="claude-sonnet-4-5",
                        input_cost_usd=Decimal("0.300000"),
                        output_cost_usd=Decimal("0.750000"),
                        cache_write_cost_usd=Decimal("0.030000"),
                        cache_read_cost_usd=Decimal("0.015000"),
                        total_cost_usd=Decimal("1.095000"),
                    )
                ]
            )
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = TokenUsageRepository(mock_session)

        user_id = uuid4()
        access_key_id = uuid4()

        results = await repo.get_cost_breakdown_by_model(
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 31, tzinfo=timezone.utc),
            user_id=user_id,
            access_key_id=access_key_id,
        )

        assert len(results) == 1

        executed_query = mock_session.execute.call_args[0][0]
        compiled = str(executed_query.compile(compile_kwargs={"literal_binds": False}))

        # Both filters should be present
        assert "user_id" in compiled
        assert "access_key_id" in compiled
