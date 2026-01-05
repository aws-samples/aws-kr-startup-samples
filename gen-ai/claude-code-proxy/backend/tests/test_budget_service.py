from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.domain import User, UserStatus
from src.proxy.budget import BudgetService, CachedBudgetInfo
from src.proxy.dependencies import ProxyDependencies, set_proxy_deps, reset_proxy_deps


@pytest.fixture
def proxy_deps():
    deps = ProxyDependencies()
    set_proxy_deps(deps)
    yield deps
    reset_proxy_deps()


def _build_user(budget: Decimal | None) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        name="user",
        description=None,
        status=UserStatus.ACTIVE,
        monthly_budget_usd=budget,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_budget_service_uses_cache_on_hit(proxy_deps):
    user_id = uuid4()
    user_repo = AsyncMock()
    usage_repo = AsyncMock()
    budget_service = BudgetService(user_repo, usage_repo)

    period_start, period_end_exclusive = budget_service.get_month_window()
    period_end = period_end_exclusive - timedelta(seconds=1)

    proxy_deps.budget_cache.set(
        str(user_id),
        CachedBudgetInfo(
            user_id=user_id,
            monthly_budget=Decimal("100.00"),
            current_usage=Decimal("10.00"),
            period_start=period_start,
            period_end=period_end,
            cached_at=datetime.now(timezone.utc),
        ),
    )

    result = await budget_service.check_budget(user_id)

    assert result.monthly_budget == Decimal("100.00")
    assert result.current_usage == Decimal("10.00")
    user_repo.get_by_id.assert_not_called()
    usage_repo.get_monthly_usage_total.assert_not_called()


@pytest.mark.asyncio
async def test_budget_service_refreshes_cache_on_month_change(proxy_deps):
    user_id = uuid4()
    user_repo = AsyncMock()
    usage_repo = AsyncMock()
    user_repo.get_by_id.return_value = _build_user(Decimal("50.00"))
    usage_repo.get_monthly_usage_total.return_value = Decimal("5.00")

    budget_service = BudgetService(user_repo, usage_repo)
    period_start, _period_end = budget_service.get_month_window()

    proxy_deps.budget_cache.set(
        str(user_id),
        CachedBudgetInfo(
            user_id=user_id,
            monthly_budget=Decimal("20.00"),
            current_usage=Decimal("2.00"),
            period_start=period_start - timedelta(days=31),
            period_end=period_start - timedelta(days=1),
            cached_at=datetime.now(timezone.utc),
        ),
    )

    result = await budget_service.check_budget(user_id)

    assert result.monthly_budget == Decimal("50.00")
    assert result.current_usage == Decimal("5.00")
    user_repo.get_by_id.assert_awaited()
    usage_repo.get_monthly_usage_total.assert_awaited()


@pytest.mark.asyncio
async def test_budget_service_fail_open_on_lookup_error(proxy_deps):
    user_id = uuid4()
    user_repo = AsyncMock()
    usage_repo = AsyncMock()
    user_repo.get_by_id.side_effect = RuntimeError("db unavailable")

    budget_service = BudgetService(user_repo, usage_repo)
    result = await budget_service.check_budget(user_id)

    assert result.allowed is True
    assert result.monthly_budget is None
    assert result.current_usage == Decimal("0")


@pytest.mark.asyncio
async def test_budget_cache_invalidation_refreshes(proxy_deps):
    user_id = uuid4()
    user_repo = AsyncMock()
    usage_repo = AsyncMock()
    user_repo.get_by_id.return_value = _build_user(Decimal("200.00"))
    usage_repo.get_monthly_usage_total.return_value = Decimal("20.00")

    budget_service = BudgetService(user_repo, usage_repo)
    period_start, period_end_exclusive = budget_service.get_month_window()
    period_end = period_end_exclusive - timedelta(seconds=1)

    proxy_deps.budget_cache.set(
        str(user_id),
        CachedBudgetInfo(
            user_id=user_id,
            monthly_budget=Decimal("50.00"),
            current_usage=Decimal("5.00"),
            period_start=period_start,
            period_end=period_end,
            cached_at=datetime.now(timezone.utc),
        ),
    )

    budget_service.invalidate_cache(user_id)

    result = await budget_service.check_budget(user_id)

    assert result.monthly_budget == Decimal("200.00")
    assert result.current_usage == Decimal("20.00")
