import importlib
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

proxy_router = importlib.import_module("src.api.proxy_router")
from src.domain import AnthropicRequest, AnthropicResponse, AnthropicUsage, ErrorType
from src.proxy.adapter_base import AdapterError, AdapterResponse
from src.proxy.budget import _build_budget_result
from src.proxy.context import RequestContext


class DummyRequest:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


class DummyUsageRecorder:
    def __init__(self, *_args, **_kwargs) -> None:
        return None

    async def record(self, *_args, **_kwargs) -> None:
        return None


@pytest.mark.asyncio
async def test_proxy_messages_budget_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, bool] = {}
    now = datetime.now(timezone.utc)

    async def _fake_check_budget(self, _user_id, *, fail_open: bool = True):
        called["fail_open"] = fail_open
        return _build_budget_result(Decimal("100.00"), Decimal("0.00"), now, now)

    async def _fake_plan_invoke(self, _ctx, _request):
        return AdapterError(
            error_type=ErrorType.RATE_LIMIT,
            status_code=429,
            message="Rate limit",
            retryable=True,
        )

    async def _fake_bedrock_invoke(self, _ctx, _request):
        usage = AnthropicUsage(input_tokens=1, output_tokens=1)
        response = AnthropicResponse(
            id="msg_test",
            content=[{"type": "text", "text": "ok"}],
            model="claude-test",
            usage=usage,
        )
        return AdapterResponse(response=response, usage=usage)

    async def _fake_authenticate(_raw_key):
        return RequestContext(
            request_id="req-test",
            user_id=uuid4(),
            access_key_id=uuid4(),
            access_key_prefix="ak",
            bedrock_region="ap-northeast-2",
            bedrock_model="anthropic.claude-sonnet-4-5-20250514",
            has_bedrock_key=True,
        )

    class FakeAuthService:
        authenticate = AsyncMock(side_effect=_fake_authenticate)

    monkeypatch.setattr(proxy_router.BudgetService, "check_budget", _fake_check_budget)
    monkeypatch.setattr(proxy_router.PlanAdapter, "invoke", _fake_plan_invoke)
    monkeypatch.setattr(proxy_router.BedrockAdapter, "invoke", _fake_bedrock_invoke)
    monkeypatch.setattr(proxy_router, "UsageRecorder", DummyUsageRecorder)

    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "hello"}],
    )
    raw_request = DummyRequest(headers={"x-api-key": "test"})
    session = AsyncMock()

    await proxy_router.proxy_messages(
        access_key="ak_test",
        request=request,
        raw_request=raw_request,
        session=session,
        auth_service=FakeAuthService(),
    )

    assert called.get("fail_open") is False
