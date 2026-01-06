from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
import importlib

import pytest
from fastapi.responses import JSONResponse, StreamingResponse

from src.domain import AnthropicRequest, AnthropicResponse, AnthropicUsage, RoutingStrategy
from src.proxy.context import RequestContext
from src.proxy.budget import _build_budget_result
from src.proxy.router import ProxyResponse

proxy_router = importlib.import_module("src.api.proxy_router")


class DummyRequest:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


@pytest.mark.asyncio
async def test_stream_bedrock_only_routes_to_bedrock(monkeypatch: pytest.MonkeyPatch) -> None:
    bedrock_calls: list = []

    class FakeBedrockAdapter:
        def __init__(self, _repo) -> None:
            return None

        async def stream(self, ctx, request):
            bedrock_calls.append((ctx, request))

            async def _gen():
                yield b"data: {}\n\n"

            return _gen()

        async def close(self) -> None:
            return None

    async def _fake_check_budget(self, _user_id, *, fail_open: bool = True):
        now = datetime.now(timezone.utc)
        return _build_budget_result(None, Decimal("0"), now, now)

    async def _fake_authenticate(_raw_key):
        return RequestContext(
            request_id="req-test",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
            routing_strategy=RoutingStrategy.BEDROCK_ONLY,
        )

    class FakeAuthService:
        authenticate = AsyncMock(side_effect=_fake_authenticate)

    monkeypatch.setattr(proxy_router, "BedrockAdapter", FakeBedrockAdapter)
    monkeypatch.setattr(proxy_router.BudgetService, "check_budget", _fake_check_budget)

    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "hello"}],
        stream=True,
    )
    raw_request = DummyRequest(headers={"x-api-key": "test"})
    session = AsyncMock()

    response = await proxy_router.proxy_messages(
        access_key="ak_test",
        request=request,
        raw_request=raw_request,
        session=session,
        auth_service=FakeAuthService(),
    )

    assert isinstance(response, StreamingResponse)
    assert response.status_code == 200
    assert bedrock_calls


@pytest.mark.asyncio
async def test_stream_bedrock_only_without_key_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bedrock_calls: list = []

    class FakeBedrockAdapter:
        def __init__(self, _repo) -> None:
            return None

        async def stream(self, ctx, request):
            bedrock_calls.append((ctx, request))

            async def _gen():
                yield b"data: {}\n\n"

            return _gen()

        async def close(self) -> None:
            return None

    async def _fake_authenticate(_raw_key):
        return RequestContext(
            request_id="req-test",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=False,
            routing_strategy=RoutingStrategy.BEDROCK_ONLY,
        )

    class FakeAuthService:
        authenticate = AsyncMock(side_effect=_fake_authenticate)

    monkeypatch.setattr(proxy_router, "BedrockAdapter", FakeBedrockAdapter)

    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "hello"}],
        stream=True,
    )
    raw_request = DummyRequest(headers={"x-api-key": "test"})
    session = AsyncMock()

    response = await proxy_router.proxy_messages(
        access_key="ak_test",
        request=request,
        raw_request=raw_request,
        session=session,
        auth_service=FakeAuthService(),
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert not bedrock_calls


# ============================================================================
# Kent Beck style: Bedrock Only does NOT create PlanAdapter (Non-streaming)
# ============================================================================

@pytest.mark.asyncio
async def test_non_streaming_bedrock_only_does_not_create_plan_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bedrock Only 라우팅 시 PlanAdapter가 생성되지 않는다 (Non-streaming)"""
    # Arrange: Track adapter creation
    plan_adapter_created = []
    bedrock_adapter_created = []

    class FakePlanAdapter:
        def __init__(self, headers=None) -> None:
            plan_adapter_created.append(True)

        async def invoke(self, ctx, request):
            raise AssertionError("PlanAdapter.invoke should not be called")

        async def close(self) -> None:
            return None

    class FakeBedrockAdapter:
        def __init__(self, _repo) -> None:
            bedrock_adapter_created.append(True)

        async def invoke(self, ctx, request):
            return Mock(
                response=AnthropicResponse(
                    id="msg-test",
                    type="message",
                    role="assistant",
                    content=[{"type": "text", "text": "Hello"}],
                    model="claude-test",
                    stop_reason="end_turn",
                    usage={"input_tokens": 10, "output_tokens": 5},
                ),
                usage=AnthropicUsage(input_tokens=10, output_tokens=5),
            )

        async def close(self) -> None:
            return None

    class FakeProxyRouter:
        def __init__(self, plan_adapter, bedrock_adapter, budget_checker=None):
            self.plan_adapter = plan_adapter
            self.bedrock_adapter = bedrock_adapter

        async def route(self, ctx, request):
            # Verify plan_adapter is None for bedrock_only
            assert self.plan_adapter is None, "PlanAdapter should be None for bedrock_only"
            return ProxyResponse(
                success=True,
                response=AnthropicResponse(
                    id="msg-test",
                    type="message",
                    role="assistant",
                    content=[{"type": "text", "text": "Hello"}],
                    model="claude-test",
                    stop_reason="end_turn",
                    usage={"input_tokens": 10, "output_tokens": 5},
                ),
                usage=AnthropicUsage(input_tokens=10, output_tokens=5),
                provider="bedrock",
                is_fallback=False,
                status_code=200,
            )

    class FakeUsageRecorder:
        def __init__(self, *args, **kwargs):
            pass

        async def record(self, *args, **kwargs):
            pass

    async def _fake_check_budget(self, _user_id, *, fail_open: bool = True):
        now = datetime.now(timezone.utc)
        return _build_budget_result(None, Decimal("0"), now, now)

    async def _fake_authenticate(_raw_key):
        return RequestContext(
            request_id="req-test",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
            routing_strategy=RoutingStrategy.BEDROCK_ONLY,
        )

    class FakeAuthService:
        authenticate = AsyncMock(side_effect=_fake_authenticate)

    monkeypatch.setattr(proxy_router, "PlanAdapter", FakePlanAdapter)
    monkeypatch.setattr(proxy_router, "BedrockAdapter", FakeBedrockAdapter)
    monkeypatch.setattr(proxy_router, "ProxyRouter", FakeProxyRouter)
    monkeypatch.setattr(proxy_router, "UsageRecorder", FakeUsageRecorder)
    monkeypatch.setattr(proxy_router.BudgetService, "check_budget", _fake_check_budget)

    # Act
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "hello"}],
        stream=False,  # Non-streaming
    )
    raw_request = DummyRequest(headers={})
    session = AsyncMock()
    session.commit = AsyncMock()

    response = await proxy_router.proxy_messages(
        access_key="ak_test",
        request=request,
        raw_request=raw_request,
        session=session,
        auth_service=FakeAuthService(),
    )

    # Assert
    assert not plan_adapter_created, "PlanAdapter should NOT be created for bedrock_only"
    assert bedrock_adapter_created, "BedrockAdapter should be created"


@pytest.mark.asyncio
async def test_non_streaming_plan_first_creates_plan_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plan First 라우팅 시 PlanAdapter가 생성된다 (Non-streaming)"""
    # Arrange: Track adapter creation
    plan_adapter_created = []
    bedrock_adapter_created = []

    class FakePlanAdapter:
        def __init__(self, headers=None) -> None:
            plan_adapter_created.append(True)

        async def invoke(self, ctx, request):
            pass

        async def close(self) -> None:
            return None

    class FakeBedrockAdapter:
        def __init__(self, _repo) -> None:
            bedrock_adapter_created.append(True)

        async def invoke(self, ctx, request):
            pass

        async def close(self) -> None:
            return None

    class FakeProxyRouter:
        def __init__(self, plan_adapter, bedrock_adapter, budget_checker=None):
            self.plan_adapter = plan_adapter
            self.bedrock_adapter = bedrock_adapter

        async def route(self, ctx, request):
            # Verify plan_adapter is NOT None for plan_first
            assert self.plan_adapter is not None, "PlanAdapter should exist for plan_first"
            return ProxyResponse(
                success=True,
                response=AnthropicResponse(
                    id="msg-test",
                    type="message",
                    role="assistant",
                    content=[{"type": "text", "text": "Hello"}],
                    model="claude-test",
                    stop_reason="end_turn",
                    usage={"input_tokens": 10, "output_tokens": 5},
                ),
                usage=AnthropicUsage(input_tokens=10, output_tokens=5),
                provider="plan",
                is_fallback=False,
                status_code=200,
            )

    class FakeUsageRecorder:
        def __init__(self, *args, **kwargs):
            pass

        async def record(self, *args, **kwargs):
            pass

    async def _fake_check_budget(self, _user_id, *, fail_open: bool = True):
        now = datetime.now(timezone.utc)
        return _build_budget_result(None, Decimal("0"), now, now)

    async def _fake_authenticate(_raw_key):
        return RequestContext(
            request_id="req-test",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
            routing_strategy=RoutingStrategy.PLAN_FIRST,  # Plan First
        )

    class FakeAuthService:
        authenticate = AsyncMock(side_effect=_fake_authenticate)

    monkeypatch.setattr(proxy_router, "PlanAdapter", FakePlanAdapter)
    monkeypatch.setattr(proxy_router, "BedrockAdapter", FakeBedrockAdapter)
    monkeypatch.setattr(proxy_router, "ProxyRouter", FakeProxyRouter)
    monkeypatch.setattr(proxy_router, "UsageRecorder", FakeUsageRecorder)
    monkeypatch.setattr(proxy_router.BudgetService, "check_budget", _fake_check_budget)

    # Act
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "hello"}],
        stream=False,  # Non-streaming
    )
    raw_request = DummyRequest(headers={})
    session = AsyncMock()
    session.commit = AsyncMock()

    response = await proxy_router.proxy_messages(
        access_key="ak_test",
        request=request,
        raw_request=raw_request,
        session=session,
        auth_service=FakeAuthService(),
    )

    # Assert
    assert plan_adapter_created, "PlanAdapter should be created for plan_first"
    assert bedrock_adapter_created, "BedrockAdapter should be created"
