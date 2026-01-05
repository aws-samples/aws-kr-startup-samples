from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4
import importlib

import pytest
from fastapi.responses import JSONResponse, StreamingResponse

from src.domain import AnthropicRequest, RoutingStrategy
from src.proxy.context import RequestContext
from src.proxy.budget import _build_budget_result

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
