from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.api import admin_users
from src.domain import User, UserStatus, UserBudgetUpdate
from src.proxy.dependencies import ProxyDependencies, set_proxy_deps, reset_proxy_deps


class FakeUserRepository:
    def __init__(self, _session) -> None:
        self.updated_budget: Decimal | None = None
        self.user = User(
            id=uuid4(),
            name="user",
            description=None,
            status=UserStatus.ACTIVE,
            monthly_budget_usd=Decimal("100.00"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def get_by_id(self, _user_id):
        return self.user

    async def update_budget(self, _user_id, budget):
        self.updated_budget = budget
        self.user = User(
            id=self.user.id,
            name=self.user.name,
            description=self.user.description,
            status=self.user.status,
            monthly_budget_usd=budget,
            created_at=self.user.created_at,
            updated_at=self.user.updated_at,
        )
        return True


class FakeUsageAggregateRepository:
    def __init__(self, _session) -> None:
        return None

    async def get_monthly_usage_total(self, *_args, **_kwargs):
        return Decimal("25.50")


@pytest.fixture(autouse=True)
def proxy_deps():
    deps = ProxyDependencies()
    set_proxy_deps(deps)
    yield
    reset_proxy_deps()


@pytest.mark.asyncio
async def test_get_user_budget_returns_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_users, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(admin_users, "UsageAggregateRepository", FakeUsageAggregateRepository)

    response = await admin_users.get_user_budget(user_id=uuid4(), session=None)

    assert response.monthly_budget_usd == "100.00"
    assert response.current_usage_usd == "25.50"
    assert response.remaining_usd == "74.50"
    assert response.usage_percentage is not None
    assert response.period_start.tzinfo is not None
    assert response.period_end.tzinfo is not None


@pytest.mark.asyncio
async def test_update_user_budget_returns_updated_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(admin_users, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(admin_users, "UsageAggregateRepository", FakeUsageAggregateRepository)
    invalidate_calls: list = []

    def _fake_invalidate(user_id):
        invalidate_calls.append(user_id)

    monkeypatch.setattr(admin_users, "invalidate_budget_cache", _fake_invalidate)

    response = await admin_users.update_user_budget(
        user_id=uuid4(),
        data=UserBudgetUpdate(monthly_budget_usd=None),
        session=None,
    )

    assert response.monthly_budget_usd is None
    assert response.remaining_usd is None
    assert invalidate_calls
