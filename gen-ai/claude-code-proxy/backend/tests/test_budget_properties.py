from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from hypothesis import given, strategies as st

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.domain import User, UserStatus, UserBudgetUpdate
from src.proxy.budget import _build_budget_result, BudgetService
from src.proxy.dependencies import ProxyDependencies, set_proxy_deps, reset_proxy_deps


budget_values = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)
usage_values = st.decimals(
    min_value=Decimal("0.00"),
    max_value=Decimal("2000000.00"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@pytest.fixture(autouse=True)
def proxy_deps():
    deps = ProxyDependencies()
    set_proxy_deps(deps)
    yield
    reset_proxy_deps()


@given(budget_values)
@pytest.mark.asyncio
async def test_budget_value_round_trip(budget):
    reset_proxy_deps()
    set_proxy_deps(ProxyDependencies())

    user = User(
        id=uuid4(),
        name="user",
        description=None,
        status=UserStatus.ACTIVE,
        monthly_budget_usd=budget,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    class FakeUserRepo:
        async def get_by_id(self, _user_id):
            return user

    class FakeUsageRepo:
        async def get_monthly_usage_total(self, *_args, **_kwargs):
            return Decimal("0")

    service = BudgetService(FakeUserRepo(), FakeUsageRepo())
    result = await service.check_budget(user.id)

    assert result.monthly_budget == budget


@given(
    st.one_of(
        st.decimals(max_value=Decimal("0.00"), places=2, allow_nan=False, allow_infinity=False),
        st.decimals(min_value=Decimal("1000000.00"), places=2, allow_nan=False, allow_infinity=False),
    )
)
def test_budget_validation_rejects_invalid_values(value):
    with pytest.raises(ValidationError):
        UserBudgetUpdate(monthly_budget_usd=value)


@given(usage_values)
def test_null_budget_means_unlimited(usage):
    now = datetime.now(timezone.utc)
    result = _build_budget_result(None, usage, now, now)

    assert result.allowed is True
    assert result.remaining is None
    assert result.usage_percentage is None


@given(budget_values, usage_values)
def test_budget_status_response_completeness(budget, usage):
    now = datetime.now(timezone.utc)
    result = _build_budget_result(budget, usage, now, now)

    assert result.remaining == budget - usage
    assert result.usage_percentage == pytest.approx(
        float((usage / budget) * Decimal("100"))
    )


@given(usage_values)
def test_unlimited_status_indication(usage):
    now = datetime.now(timezone.utc)
    result = _build_budget_result(None, usage, now, now)

    assert result.monthly_budget is None
    assert result.remaining is None
    assert result.usage_percentage is None
