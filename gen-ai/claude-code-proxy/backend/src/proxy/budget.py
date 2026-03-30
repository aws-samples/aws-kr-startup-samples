from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from uuid import UUID

from ..repositories import UserRepository, UsageAggregateRepository, GroupRepository
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
    group_budget_exceeded: bool = False


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
        group_repo: GroupRepository | None = None,
    ):
        self._user_repo = user_repo
        self._usage_repo = usage_repo
        self._group_repo = group_repo
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
        return await self._usage_repo.get_monthly_usage_total(
            user_id, start_utc, end_utc, provider="bedrock"
        )

    async def check_budget(
        self, user_id: UUID, *, group_id: UUID | None = None, fail_open: bool = True
    ) -> BudgetCheckResult:
        period_start, period_end_exclusive = self.get_month_window()
        period_end = period_end_exclusive - timedelta(seconds=1)

        # User budget check
        user_result = await self._check_user_budget(
            user_id, period_start, period_end, fail_open=fail_open
        )

        # Group budget check
        if group_id and self._group_repo:
            group_result = await self._check_group_budget(
                group_id, period_start, period_end, fail_open=fail_open
            )
            if not group_result.allowed:
                return group_result
            # If user budget is also exceeded, return user result
            if not user_result.allowed:
                return user_result
            # Both allowed — return user result (more granular)
            return user_result

        return user_result

    async def _check_user_budget(
        self,
        user_id: UUID,
        period_start: datetime,
        period_end: datetime,
        *,
        fail_open: bool = True,
    ) -> BudgetCheckResult:
        cache_key = f"user:{user_id}"

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

    async def _check_group_budget(
        self,
        group_id: UUID,
        period_start: datetime,
        period_end: datetime,
        *,
        fail_open: bool = True,
    ) -> BudgetCheckResult:
        cache_key = f"group:{group_id}"

        cached = self._cache.get(cache_key)
        if isinstance(cached, CachedBudgetInfo) and cached.period_start == period_start:
            result = _build_budget_result(
                cached.monthly_budget,
                cached.current_usage,
                cached.period_start,
                cached.period_end,
            )
            if not result.allowed:
                result.group_budget_exceeded = True
            return result

        try:
            group = await self._group_repo.get_by_id(group_id)
            monthly_budget = group.monthly_budget_usd if group else None
            start_utc = period_start.astimezone(timezone.utc)
            end_utc = (period_end + timedelta(seconds=1)).astimezone(timezone.utc)
            current_usage = await self._usage_repo.get_group_monthly_usage_total(
                group_id, start_utc, end_utc, provider="bedrock"
            )
        except Exception:
            if fail_open:
                return _build_budget_result(None, Decimal("0"), period_start, period_end)
            raise

        self._cache.set(
            cache_key,
            CachedBudgetInfo(
                user_id=group_id,  # reuse field for group_id
                monthly_budget=monthly_budget,
                current_usage=current_usage,
                period_start=period_start,
                period_end=period_end,
                cached_at=datetime.now(timezone.utc),
            ),
        )

        result = _build_budget_result(monthly_budget, current_usage, period_start, period_end)
        if not result.allowed:
            result.group_budget_exceeded = True
        return result

    def invalidate_cache(self, user_id: UUID) -> None:
        self._cache.invalidate(f"user:{user_id}")

    def invalidate_group_cache(self, group_id: UUID) -> None:
        self._cache.invalidate(f"group:{group_id}")


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
    scope = "Group monthly budget" if result.group_budget_exceeded else "Monthly budget"
    return (
        f"{scope} exceeded. "
        f"Current usage: ${usage}, Budget limit: ${budget}. "
        f"Budget resets on {reset_at}."
    )


def _format_usd(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def invalidate_budget_cache(user_id: UUID) -> None:
    get_proxy_deps().budget_cache.invalidate(f"user:{user_id}")
