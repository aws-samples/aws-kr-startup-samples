from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
import sys
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, assume

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.proxy.router import ProxyRouter
from src.proxy.budget import _build_budget_result
from src.proxy.adapter_base import Adapter, AdapterError
from src.proxy.context import RequestContext
from src.proxy.dependencies import ProxyDependencies, set_proxy_deps
from src.domain import AnthropicRequest, ErrorType, RETRYABLE_ERRORS
from src.proxy.circuit_breaker import CircuitBreaker


@pytest.fixture
def mock_circuit_breaker():
    cb = Mock(spec=CircuitBreaker)
    cb.is_open.return_value = False
    return cb


@pytest.fixture(autouse=True)
def setup_dependencies(mock_circuit_breaker):
    deps = ProxyDependencies(circuit_breaker=mock_circuit_breaker)
    set_proxy_deps(deps)
    yield


budget_values = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("1000.00"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)
usage_values = st.decimals(
    min_value=Decimal("0.00"),
    max_value=Decimal("2000.00"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@given(budget_values, usage_values)
@pytest.mark.asyncio
async def test_budget_exceeded_rejects_before_bedrock_call(budget, usage):
    assume(usage >= budget)

    plan_adapter = Mock(spec=Adapter)
    bedrock_adapter = Mock(spec=Adapter)
    plan_adapter.invoke = AsyncMock(
        return_value=AdapterError(
            error_type=list(RETRYABLE_ERRORS)[0],
            status_code=429,
            message="Rate limit",
            retryable=True,
        )
    )
    bedrock_adapter.invoke = AsyncMock()

    ctx = RequestContext(
        request_id="req-test",
        user_id=uuid4(),
        access_key_id=uuid4(),
        access_key_prefix="ak",
        bedrock_region="ap-northeast-2",
        bedrock_model="anthropic.claude-sonnet-4-5-20250514",
        has_bedrock_key=True,
    )
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "hello"}],
    )
    period = datetime.now(timezone.utc)
    budget_result = _build_budget_result(budget, usage, period, period)

    async def _budget_checker(_ctx):
        return budget_result

    router = ProxyRouter(plan_adapter, bedrock_adapter, budget_checker=_budget_checker)
    response = await router.route(ctx, request)

    assert response.status_code == 429
    assert response.error_type == "rate_limit_error"
    formatted_usage = f"{usage.quantize(Decimal('0.01')):.2f}"
    formatted_budget = f"{budget.quantize(Decimal('0.01')):.2f}"
    assert formatted_usage in response.error_message
    assert formatted_budget in response.error_message
    bedrock_adapter.invoke.assert_not_called()


@given(budget_values, usage_values)
@pytest.mark.asyncio
async def test_budget_check_blocks_bedrock_invocation(budget, usage):
    assume(usage >= budget)

    plan_adapter = Mock(spec=Adapter)
    bedrock_adapter = Mock(spec=Adapter)
    plan_adapter.invoke = AsyncMock(
        return_value=AdapterError(
            error_type=ErrorType.SERVER_ERROR,
            status_code=503,
            message="Upstream error",
            retryable=True,
        )
    )
    bedrock_adapter.invoke = AsyncMock()

    ctx = RequestContext(
        request_id="req-test",
        user_id=uuid4(),
        access_key_id=uuid4(),
        access_key_prefix="ak",
        bedrock_region="ap-northeast-2",
        bedrock_model="anthropic.claude-sonnet-4-5-20250514",
        has_bedrock_key=True,
    )
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "hello"}],
    )
    period = datetime.now(timezone.utc)
    budget_result = _build_budget_result(budget, usage, period, period)

    async def _budget_checker(_ctx):
        return budget_result

    router = ProxyRouter(plan_adapter, bedrock_adapter, budget_checker=_budget_checker)
    await router.route(ctx, request)

    bedrock_adapter.invoke.assert_not_called()
