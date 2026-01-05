"""Tests for _resolve_time_range() edge cases.

These tests cover boundary conditions for time range resolution
including month boundaries, date range validation, and KST timezone handling.
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.api.admin_usage import _resolve_time_range, _get_week_start_kst

KST = ZoneInfo("Asia/Seoul")


class TestResolveTimeRangePeriods:
    """Test period-based time range resolution."""

    def test_period_day_starts_at_midnight_kst(self) -> None:
        """Verify day period starts at midnight KST."""
        # 2025-01-15 15:30 KST (06:30 UTC)
        now_utc = datetime(2025, 1, 15, 6, 30, tzinfo=timezone.utc)

        start_utc, end_utc = _resolve_time_range(
            period="day",
            start_date=None,
            end_date=None,
            now_utc=now_utc,
        )

        # Start should be 2025-01-15 00:00 KST = 2025-01-14 15:00 UTC
        expected_start = datetime(2025, 1, 14, 15, 0, tzinfo=timezone.utc)
        assert start_utc == expected_start
        assert end_utc == now_utc

    def test_period_week_starts_on_sunday_kst(self) -> None:
        """Verify week period starts on Sunday 00:00 KST."""
        # 2025-01-08 Wednesday 12:00 KST (03:00 UTC)
        now_utc = datetime(2025, 1, 8, 3, 0, tzinfo=timezone.utc)

        start_utc, end_utc = _resolve_time_range(
            period="week",
            start_date=None,
            end_date=None,
            now_utc=now_utc,
        )

        # Week starts Sunday 2025-01-05 00:00 KST = 2025-01-04 15:00 UTC
        expected_start = datetime(2025, 1, 4, 15, 0, tzinfo=timezone.utc)
        assert start_utc == expected_start
        assert end_utc == now_utc

    def test_period_month_starts_on_first_day_kst(self) -> None:
        """Verify month period starts on 1st day 00:00 KST."""
        # 2025-01-20 10:00 KST (01:00 UTC)
        now_utc = datetime(2025, 1, 20, 1, 0, tzinfo=timezone.utc)

        start_utc, end_utc = _resolve_time_range(
            period="month",
            start_date=None,
            end_date=None,
            now_utc=now_utc,
        )

        # Month starts 2025-01-01 00:00 KST = 2024-12-31 15:00 UTC
        expected_start = datetime(2024, 12, 31, 15, 0, tzinfo=timezone.utc)
        assert start_utc == expected_start
        assert end_utc == now_utc

    def test_period_month_february_boundary(self) -> None:
        """Verify February month period handles correctly."""
        # 2025-02-15 12:00 KST (03:00 UTC)
        now_utc = datetime(2025, 2, 15, 3, 0, tzinfo=timezone.utc)

        start_utc, end_utc = _resolve_time_range(
            period="month",
            start_date=None,
            end_date=None,
            now_utc=now_utc,
        )

        # Month starts 2025-02-01 00:00 KST = 2025-01-31 15:00 UTC
        expected_start = datetime(2025, 1, 31, 15, 0, tzinfo=timezone.utc)
        assert start_utc == expected_start


class TestResolveTimeRangeDateRange:
    """Test explicit date range resolution."""

    def test_date_range_converts_to_kst_boundaries(self) -> None:
        """Verify date range uses KST midnight boundaries."""
        start_utc, end_utc = _resolve_time_range(
            period=None,
            start_date=date(2025, 1, 10),
            end_date=date(2025, 1, 15),
        )

        # Start: 2025-01-10 00:00 KST = 2025-01-09 15:00 UTC
        expected_start = datetime(2025, 1, 9, 15, 0, tzinfo=timezone.utc)
        # End: 2025-01-16 00:00 KST = 2025-01-15 15:00 UTC (exclusive)
        expected_end = datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc)

        assert start_utc == expected_start
        assert end_utc == expected_end

    def test_date_range_single_day(self) -> None:
        """Verify single day range covers full 24 hours in KST."""
        start_utc, end_utc = _resolve_time_range(
            period=None,
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15),
        )

        # Start: 2025-01-15 00:00 KST = 2025-01-14 15:00 UTC
        # End: 2025-01-16 00:00 KST = 2025-01-15 15:00 UTC
        expected_start = datetime(2025, 1, 14, 15, 0, tzinfo=timezone.utc)
        expected_end = datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc)

        assert start_utc == expected_start
        assert end_utc == expected_end

    def test_date_range_end_of_month(self) -> None:
        """Verify end-of-month date range handles correctly."""
        start_utc, end_utc = _resolve_time_range(
            period=None,
            start_date=date(2025, 1, 31),
            end_date=date(2025, 1, 31),
        )

        # End is exclusive next day: 2025-02-01 00:00 KST
        expected_end = datetime(2025, 1, 31, 15, 0, tzinfo=timezone.utc)
        assert end_utc == expected_end

    def test_date_range_cross_month(self) -> None:
        """Verify date range spanning month boundary."""
        start_utc, end_utc = _resolve_time_range(
            period=None,
            start_date=date(2025, 1, 28),
            end_date=date(2025, 2, 3),
        )

        # Start: 2025-01-28 00:00 KST
        # End: 2025-02-04 00:00 KST
        expected_start = datetime(2025, 1, 27, 15, 0, tzinfo=timezone.utc)
        expected_end = datetime(2025, 2, 3, 15, 0, tzinfo=timezone.utc)

        assert start_utc == expected_start
        assert end_utc == expected_end


class TestResolveTimeRangeValidation:
    """Test input validation for time range resolution."""

    def test_raises_error_when_only_start_date_provided(self) -> None:
        """Verify HTTPException raised when only start_date is given."""
        with pytest.raises(HTTPException) as exc_info:
            _resolve_time_range(
                period=None,
                start_date=date(2025, 1, 1),
                end_date=None,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid date range" in exc_info.value.detail

    def test_raises_error_when_only_end_date_provided(self) -> None:
        """Verify HTTPException raised when only end_date is given."""
        with pytest.raises(HTTPException) as exc_info:
            _resolve_time_range(
                period=None,
                start_date=None,
                end_date=date(2025, 1, 1),
            )

        assert exc_info.value.status_code == 400
        assert "Invalid date range" in exc_info.value.detail

    def test_raises_error_for_invalid_period(self) -> None:
        """Verify HTTPException raised for unknown period value."""
        with pytest.raises(HTTPException) as exc_info:
            _resolve_time_range(
                period="quarter",  # Invalid period
                start_date=None,
                end_date=None,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid period" in exc_info.value.detail


class TestResolveTimeRangeDefaults:
    """Test default time range behavior."""

    def test_default_is_last_24_hours(self) -> None:
        """Verify no params returns last 24 hours from now."""
        now_utc = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)

        start_utc, end_utc = _resolve_time_range(
            period=None,
            start_date=None,
            end_date=None,
            now_utc=now_utc,
        )

        now_kst = now_utc.astimezone(KST)
        expected_start = (now_kst - __import__("datetime").timedelta(hours=24)).astimezone(
            timezone.utc
        )

        assert end_utc == now_utc
        assert start_utc == expected_start


class TestGetWeekStartKst:
    """Test _get_week_start_kst helper function."""

    def test_monday_returns_previous_sunday(self) -> None:
        """Verify Monday returns previous Sunday as week start."""
        ts = datetime(2025, 1, 6, 12, 30, tzinfo=KST)  # Monday

        week_start = _get_week_start_kst(ts)

        assert week_start == datetime(2025, 1, 5, 0, 0, tzinfo=KST)

    def test_sunday_returns_same_day(self) -> None:
        """Verify Sunday returns same day as week start."""
        ts = datetime(2025, 1, 5, 18, 45, tzinfo=KST)  # Sunday

        week_start = _get_week_start_kst(ts)

        assert week_start == datetime(2025, 1, 5, 0, 0, tzinfo=KST)

    def test_saturday_returns_previous_sunday(self) -> None:
        """Verify Saturday returns Sunday of the same week."""
        ts = datetime(2025, 1, 11, 23, 59, tzinfo=KST)  # Saturday

        week_start = _get_week_start_kst(ts)

        assert week_start == datetime(2025, 1, 5, 0, 0, tzinfo=KST)

    def test_wednesday_returns_previous_sunday(self) -> None:
        """Verify Wednesday returns previous Sunday."""
        ts = datetime(2025, 1, 8, 9, 0, tzinfo=KST)  # Wednesday

        week_start = _get_week_start_kst(ts)

        assert week_start == datetime(2025, 1, 5, 0, 0, tzinfo=KST)

    def test_preserves_timezone(self) -> None:
        """Verify returned datetime has same timezone."""
        ts = datetime(2025, 1, 8, 12, 0, tzinfo=KST)

        week_start = _get_week_start_kst(ts)

        assert week_start.tzinfo == KST

    def test_clears_time_components(self) -> None:
        """Verify time is set to midnight."""
        ts = datetime(2025, 1, 8, 15, 45, 30, 123456, tzinfo=KST)

        week_start = _get_week_start_kst(ts)

        assert week_start.hour == 0
        assert week_start.minute == 0
        assert week_start.second == 0
        assert week_start.microsecond == 0


class TestTimeRangeEdgeCases:
    """Test edge cases in time range resolution."""

    def test_new_years_eve_to_new_years_day(self) -> None:
        """Verify date range across year boundary."""
        start_utc, end_utc = _resolve_time_range(
            period=None,
            start_date=date(2024, 12, 31),
            end_date=date(2025, 1, 1),
        )

        # Verify both dates are covered
        expected_start = datetime(2024, 12, 30, 15, 0, tzinfo=timezone.utc)  # Dec 31 00:00 KST
        expected_end = datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc)  # Jan 2 00:00 KST

        assert start_utc == expected_start
        assert end_utc == expected_end

    def test_utc_midnight_crosses_kst_day_boundary(self) -> None:
        """Verify UTC midnight (09:00 KST) is handled correctly."""
        # UTC midnight = 09:00 KST same day
        now_utc = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)

        start_utc, end_utc = _resolve_time_range(
            period="day",
            start_date=None,
            end_date=None,
            now_utc=now_utc,
        )

        # At UTC midnight, it's 09:00 KST Jan 15
        # Day starts at 00:00 KST Jan 15 = 15:00 UTC Jan 14
        expected_start = datetime(2025, 1, 14, 15, 0, tzinfo=timezone.utc)
        assert start_utc == expected_start

    def test_late_evening_kst_same_utc_day(self) -> None:
        """Verify late evening KST (early UTC) is handled correctly."""
        # 23:00 KST Jan 15 = 14:00 UTC Jan 15
        now_utc = datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc)

        start_utc, end_utc = _resolve_time_range(
            period="day",
            start_date=None,
            end_date=None,
            now_utc=now_utc,
        )

        # Day starts at 00:00 KST Jan 15 = 15:00 UTC Jan 14
        expected_start = datetime(2025, 1, 14, 15, 0, tzinfo=timezone.utc)
        assert start_utc == expected_start
