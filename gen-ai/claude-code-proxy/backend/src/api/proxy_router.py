import asyncio
import re
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import async_session_factory, get_session
from ..domain import (
    AnthropicError,
    AnthropicRequest,
    AnthropicUsage,
    Provider,
)
from ..logging import get_logger
from ..proxy import (
    AuthService,
    BedrockAdapter,
    BudgetService,
    UsageRecorder,
    get_auth_service,
    get_proxy_deps,
)
from ..proxy.adapter_base import AdapterError
from ..proxy.budget import format_budget_exceeded_message
from ..proxy.context import RequestContext
from ..proxy.router import _map_error_type
from ..proxy.streaming_usage import StreamingUsageCollector
from ..proxy.thinking_normalizer import normalize_thinking_request
from ..repositories import (
    BedrockKeyRepository,
    TokenUsageRepository,
    UsageAggregateRepository,
    UserRepository,
)

logger = get_logger(__name__)

router = APIRouter()


def _mask_access_key(path: str) -> str:
    """Mask access key in path: /ak/ak_abc123xyz -> /ak/***"""
    return re.sub(r"/ak/[^/]+", "/ak/***", path)


def _extract_request_info(raw_request: Request) -> tuple[str, str]:
    method = getattr(raw_request, "method", "unknown")
    url = getattr(raw_request, "url", None)
    path = getattr(url, "path", "unknown") if url else "unknown"
    return method, _mask_access_key(path)


def _get_bedrock_model(request: AnthropicRequest) -> str:
    return get_proxy_deps().bedrock_model_resolver.resolve(request.model)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _extract_access_key(raw_request: Request) -> str | None:
    """Extract access_key from Authorization Bearer or X-Api-Key header."""
    if auth := raw_request.headers.get("authorization"):
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            if token.startswith("ak_"):
                return token
    if api_key := raw_request.headers.get("x-api-key"):
        if api_key.startswith("ak_"):
            return api_key
    return None


@router.post("/ak/{access_key}/v1/messages")
async def proxy_messages(
    access_key: str,
    request: AnthropicRequest,
    raw_request: Request,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await _handle_messages(access_key, request, raw_request, session, auth_service)


@router.post("/v1/messages")
async def proxy_messages_header_auth(
    request: AnthropicRequest,
    raw_request: Request,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate via Bearer/X-Api-Key header (for apiKeyHelper SSO flow)."""
    access_key = _extract_access_key(raw_request)
    if not access_key:
        raise HTTPException(status_code=401, detail="Missing access key in auth headers")
    return await _handle_messages(access_key, request, raw_request, session, auth_service)


@router.get("/health")
async def health():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Core handler
# ---------------------------------------------------------------------------

async def _handle_messages(
    access_key: str,
    request: AnthropicRequest,
    raw_request: Request,
    session: AsyncSession,
    auth_service: AuthService,
):
    start_time = time.time()

    ctx = await auth_service.authenticate(access_key)
    if not ctx:
        raise HTTPException(status_code=404, detail="Not found")

    normalize_thinking_request(request)

    method, path = _extract_request_info(raw_request)
    logger.info("api_request", request_id=ctx.request_id, method=method, path=path)

    from ..repositories import GroupRepository

    usage_aggregate_repo = UsageAggregateRepository(session)
    group_repo = GroupRepository(session) if ctx.group_id else None
    budget_service = BudgetService(UserRepository(session), usage_aggregate_repo, group_repo=group_repo)

    if request.stream:
        return await _stream_bedrock(ctx, request, session, budget_service, usage_aggregate_repo)

    # Non-streaming
    return await _invoke_bedrock(ctx, request, session, budget_service, usage_aggregate_repo, start_time)


# ---------------------------------------------------------------------------
# Non-streaming Bedrock
# ---------------------------------------------------------------------------

async def _invoke_bedrock(
    ctx: RequestContext,
    request: AnthropicRequest,
    session: AsyncSession,
    budget_service: BudgetService,
    usage_aggregate_repo: UsageAggregateRepository,
    start_time: float,
):
    if not ctx.has_bedrock_key:
        return _bedrock_not_configured_error(ctx)

    budget_result = await budget_service.check_budget(ctx.user_id, group_id=ctx.group_id, fail_open=False)
    if not budget_result.allowed:
        return _budget_exceeded_error(ctx, budget_result)

    bedrock_adapter = BedrockAdapter(BedrockKeyRepository(session))
    token_usage_repo = TokenUsageRepository(session)
    usage_recorder = UsageRecorder(
        token_usage_repo, usage_aggregate_repo, session_factory=async_session_factory,
    )

    try:
        result = await bedrock_adapter.invoke(ctx, request)
        latency_ms = int((time.time() - start_time) * 1000)

        from ..proxy.router import ProxyResponse
        if isinstance(result, AdapterError):
            response = ProxyResponse(
                success=False, response=None, usage=None, provider="bedrock",
                is_fallback=False, status_code=result.status_code,
                error_type=_map_error_type(result.error_type), error_message=result.message,
            )
        else:
            response = ProxyResponse(
                success=True, response=result.response, usage=result.usage,
                provider="bedrock", is_fallback=False, status_code=200,
            )

        await usage_recorder.record(ctx, response, latency_ms, _get_bedrock_model(request))
        await session.commit()

        if response.success and response.response:
            return response.response.model_dump()

        error_body = AnthropicError(
            error={"type": response.error_type, "message": response.error_message},
            request_id=ctx.request_id,
        ).model_dump()
        return JSONResponse(content=error_body, status_code=response.status_code)
    finally:
        await bedrock_adapter.close()


# ---------------------------------------------------------------------------
# Streaming Bedrock
# ---------------------------------------------------------------------------

async def _stream_bedrock(
    ctx: RequestContext,
    request: AnthropicRequest,
    session: AsyncSession,
    budget_service: BudgetService,
    usage_aggregate_repo: UsageAggregateRepository,
):
    if not ctx.has_bedrock_key:
        return _bedrock_not_configured_error(ctx)

    budget_result = await budget_service.check_budget(ctx.user_id, group_id=ctx.group_id, fail_open=False)
    if not budget_result.allowed:
        return _budget_exceeded_error(ctx, budget_result)

    bedrock_adapter = BedrockAdapter(BedrockKeyRepository(session))
    streaming_started = False
    try:
        bedrock_result = await bedrock_adapter.stream(ctx, request)
        if isinstance(bedrock_result, AdapterError):
            error_body = AnthropicError(
                error={
                    "type": _map_error_type(bedrock_result.error_type),
                    "message": bedrock_result.message,
                },
                request_id=ctx.request_id,
            ).model_dump()
            return JSONResponse(content=error_body, status_code=bedrock_result.status_code)

        streaming_started = True
        return _build_streaming_response(
            ctx, request, session, usage_aggregate_repo, bedrock_adapter, bedrock_result,
        )
    finally:
        if not streaming_started:
            await bedrock_adapter.close()


def _build_streaming_response(
    ctx: RequestContext,
    request: AnthropicRequest,
    session: AsyncSession,
    usage_aggregate_repo: UsageAggregateRepository,
    bedrock_adapter: BedrockAdapter,
    bedrock_result: AsyncIterator[bytes],
) -> StreamingResponse:
    streaming_start = time.time()
    usage_recorder = UsageRecorder(
        TokenUsageRepository(session), usage_aggregate_repo,
        session_factory=async_session_factory,
    )
    usage_collector = StreamingUsageCollector()

    async def stream_generator():
        ttft_ms: int | None = None
        try:
            async for chunk in bedrock_result:
                usage_collector.feed(chunk)
                if ttft_ms is None:
                    ttft_ms = int((time.time() - streaming_start) * 1000)
                yield chunk
        finally:
            try:
                await asyncio.shield(bedrock_adapter.close())
            finally:
                usage = usage_collector.get_usage()
                if usage:
                    latency_ms = int((time.time() - streaming_start) * 1000)
                    await asyncio.shield(
                        usage_recorder.record_streaming_usage(
                            ctx, usage, latency_ms, _get_bedrock_model(request),
                            is_fallback=False, provider="bedrock", ttft_ms=ttft_ms,
                        )
                    )

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def _bedrock_not_configured_error(ctx: RequestContext):
    error_body = AnthropicError(
        error={"type": "api_error", "message": "Bedrock key not configured"},
        request_id=ctx.request_id,
    ).model_dump()
    return JSONResponse(content=error_body, status_code=503)


def _budget_exceeded_error(ctx: RequestContext, budget_result):
    error_body = AnthropicError(
        error={
            "type": "rate_limit_error",
            "message": format_budget_exceeded_message(budget_result),
        },
        request_id=ctx.request_id,
    ).model_dump()
    return JSONResponse(content=error_body, status_code=429)
