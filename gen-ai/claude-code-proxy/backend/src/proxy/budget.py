from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from uuid import UUID

from ..repositories import UserRepository, UsageAggregateRepository
from .dependencies import get_proxy_deps


@dataclass
class BudgetCheckResult:
    allowed: bool
    monthly_budget: Decimal | None
    current_usage: Decimal
    remaining: Decimal | None
    usage_percentage: float | None
    period_start: datetime
    period_end: datetime


@dataclass
class CachedBudgetInfo:
    user_id: UUID
    monthly_budget: Decimal | None
    current_usage: Decimal
    period_start: datetime
    period_end: datetime
    cached_at: datetime


class BudgetService:
    """Budget checks backed by usage aggregates."""

    KST = ZoneInfo("Asia/Seoul")

    def __init__(
        self,
        user_repo: UserRepository,
        usage_repo: UsageAggregateRepository,
    ):
        self._user_repo = user_repo
        self._usage_repo = usage_repo
        self._cache = get_proxy_deps().budget_cache

    def get_month_window(self, now: datetime | None = None) -> tuple[datetime, datetime]:
        now_kst = (now or datetime.now(timezone.utc)).astimezone(self.KST)
        start = now_kst.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    async def get_user_budget(self, user_id: UUID) -> Decimal | None:
        user = await self._user_repo.get_by_id(user_id)
        return user.monthly_budget_usd if user else None

    async def get_current_month_usage(self, user_id: UUID) -> Decimal:
        start_kst, end_kst = self.get_month_window()
        start_utc = start_kst.astimezone(timezone.utc)
        end_utc = end_kst.astimezone(timezone.utc)
        return await self._usage_repo.get_monthly_usage_total(user_id, start_utc, end_utc)

    async def check_budget(
        self, user_id: UUID, *, fail_open: bool = True
    ) -> BudgetCheckResult:
        period_start, period_end_exclusive = self.get_month_window()
        period_end = period_end_exclusive - timedelta(seconds=1)
        cache_key = str(user_id)

        cached = self._cache.get(cache_key)
        if isinstance(cached, CachedBudgetInfo) and cached.period_start == period_start:
            return _build_budget_result(
                cached.monthly_budget,
                cached.current_usage,
                cached.period_start,
                cached.period_end,
            )

        try:
            monthly_budget = await self.get_user_budget(user_id)
            current_usage = await self.get_current_month_usage(user_id)
        except Exception:
            if fail_open:
                return _build_budget_result(None, Decimal("0"), period_start, period_end)
            raise

        self._cache.set(
            cache_key,
            CachedBudgetInfo(
                user_id=user_id,
                monthly_budget=monthly_budget,
                current_usage=current_usage,
                period_start=period_start,
                period_end=period_end,
                cached_at=datetime.now(timezone.utc),
            ),
        )

        return _build_budget_result(monthly_budget, current_usage, period_start, period_end)

    def invalidate_cache(self, user_id: UUID) -> None:
        self._cache.invalidate(str(user_id))


def _build_budget_result(
    monthly_budget: Decimal | None,
    current_usage: Decimal,
    period_start: datetime,
    period_end: datetime,
) -> BudgetCheckResult:
    if monthly_budget is None:
        return BudgetCheckResult(
            allowed=True,
            monthly_budget=None,
            current_usage=current_usage,
            remaining=None,
            usage_percentage=None,
            period_start=period_start,
            period_end=period_end,
        )

    allowed = current_usage < monthly_budget
    remaining = monthly_budget - current_usage
    usage_percentage = (
        float((current_usage / monthly_budget) * Decimal("100"))
        if monthly_budget > 0
        else None
    )

    return BudgetCheckResult(
        allowed=allowed,
        monthly_budget=monthly_budget,
        current_usage=current_usage,
        remaining=remaining,
        usage_percentage=usage_percentage,
        period_start=period_start,
        period_end=period_end,
    )


def format_budget_exceeded_message(result: BudgetCheckResult) -> str:
    usage = _format_usd(result.current_usage)
    budget = _format_usd(
        result.monthly_budget if result.monthly_budget is not None else Decimal("0")
    )
    reset_at = result.period_end.strftime("%Y-%m-%d %H:%M:%S %Z")
    return (
        "Monthly budget exceeded. "
        f"Current usage: ${usage}, Budget limit: ${budget}. "
        f"Budget resets on {reset_at}."
    )


def _format_usd(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def invalidate_budget_cache(user_id: UUID) -> None:
    get_proxy_deps().budget_cache.invalidate(str(user_id))
