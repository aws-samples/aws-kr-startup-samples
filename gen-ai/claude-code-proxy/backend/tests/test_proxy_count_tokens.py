import importlib
from unittest.mock import AsyncMock
from uuid import uuid4
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

proxy_router = importlib.import_module("src.api.proxy_router")
from src.domain import AnthropicRequest, AnthropicCountTokensResponse
from src.proxy.context import RequestContext


class DummyRequest:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


@pytest.mark.asyncio
async def test_count_tokens_bypass_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_count_tokens(self, _request, request_id=None):
        return AnthropicCountTokensResponse(input_tokens=123)

    async def _fake_authenticate(_raw_key):
        return RequestContext(
            request_id="req-count",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )

    class FakeAuthService:
        authenticate = AsyncMock(side_effect=_fake_authenticate)

    monkeypatch.setattr(proxy_router.PlanAdapter, "count_tokens", _fake_count_tokens)

    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "hello"}],
    )
    raw_request = DummyRequest(headers={"x-api-key": "test"})

    response = await proxy_router.proxy_count_tokens(
        access_key="ak_test",
        request=request,
        raw_request=raw_request,
        auth_service=FakeAuthService(),
    )

    assert response == {"input_tokens": 123}
