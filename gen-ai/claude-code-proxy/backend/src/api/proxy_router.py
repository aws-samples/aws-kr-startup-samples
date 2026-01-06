import asyncio
import time
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import async_session_factory, get_session
from ..domain import (
    RETRYABLE_ERRORS,
    AnthropicCountTokensResponse,
    AnthropicError,
    AnthropicRequest,
    AnthropicUsage,
    RoutingStrategy,
)
from ..logging import get_logger
from ..proxy import (
    AuthService,
    BedrockAdapter,
    BudgetService,
    PlanAdapter,
    ProxyRouter,
    UsageRecorder,
    get_auth_service,
)
from ..proxy.adapter_base import AdapterError
from ..proxy.budget import format_budget_exceeded_message
from ..proxy.context import RequestContext
from ..proxy.router import _map_error_type
from ..proxy.streaming_usage import StreamingUsageCollector
from ..proxy.thinking_normalizer import (
    ensure_thinking_prefix,
    remove_invalid_redacted_thinking,
    should_drop_thinking_param,
)
from ..repositories import (
    BedrockKeyRepository,
    TokenUsageRepository,
    UsageAggregateRepository,
    UserRepository,
)

logger = get_logger(__name__)

router = APIRouter()

_PASSTHROUGH_HEADERS = ("anthropic-version", "anthropic-beta", "content-type")


def _extract_outgoing_headers(raw_request: Request) -> dict[str, str]:
    """Extract auth and passthrough headers from incoming request."""
    headers: dict[str, str] = {}
    if x_api_key := raw_request.headers.get("x-api-key"):
        headers["x-api-key"] = x_api_key
    if authorization := raw_request.headers.get("authorization"):
        headers["Authorization"] = authorization
    for name in _PASSTHROUGH_HEADERS:
        if value := raw_request.headers.get(name):
            headers[name] = value
    return headers


@router.post("/ak/{access_key}/v1/messages")
async def proxy_messages(
    access_key: str,
    request: AnthropicRequest,
    raw_request: Request,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    start_time = time.time()

    # Authenticate
    ctx = await auth_service.authenticate(access_key)
    if not ctx:
        raise HTTPException(status_code=404, detail="Not found")

    outgoing_headers = _extract_outgoing_headers(raw_request)

    # LiteLLM 방식: invalid redacted_thinking 제거 → thinking 블록 정리 → thinking param 드롭 체크
    remove_invalid_redacted_thinking(request)
    ensure_thinking_prefix(request)
    if should_drop_thinking_param(request):
        request.thinking = None

    logger.info(
        "proxy_request_received",
        request_id=ctx.request_id,
        user_id=str(ctx.user_id),
        access_key_id=str(ctx.access_key_id),
        routing_strategy=ctx.routing_strategy.value,
        has_bedrock_key=ctx.has_bedrock_key,
        model=request.model,
        stream=request.stream,
        max_tokens=request.max_tokens,
    )

    usage_aggregate_repo = UsageAggregateRepository(session)
    budget_service = BudgetService(UserRepository(session), usage_aggregate_repo)

    if request.stream:
        # Route streaming based on user's routing strategy
        if ctx.routing_strategy == RoutingStrategy.BEDROCK_ONLY:
            return await _stream_bedrock_only(
                ctx, request, session, budget_service, usage_aggregate_repo
            )

        # Default: plan_first streaming
        return await _stream_plan_first(
            ctx, request, session, outgoing_headers, budget_service, usage_aggregate_repo
        )

    # Setup adapters
    token_usage_repo = TokenUsageRepository(session)

    # Bedrock Only 사용자는 PlanAdapter 불필요
    plan_adapter = None if ctx.routing_strategy == RoutingStrategy.BEDROCK_ONLY else PlanAdapter(headers=outgoing_headers)
    bedrock_adapter = BedrockAdapter(BedrockKeyRepository(session))

    async def _budget_checker(ctx):
        return await budget_service.check_budget(ctx.user_id, fail_open=False)

    proxy_router = ProxyRouter(
        plan_adapter,
        bedrock_adapter,
        budget_checker=_budget_checker,
    )
    usage_recorder = UsageRecorder(
        token_usage_repo,
        usage_aggregate_repo,
        session_factory=async_session_factory,
    )

    try:
        # Route request
        response = await proxy_router.route(ctx, request)
        logger.info(
            "proxy_route_result",
            request_id=ctx.request_id,
            provider=response.provider,
            is_fallback=response.is_fallback,
            status_code=response.status_code,
            error_type=response.error_type,
            routing_strategy=ctx.routing_strategy.value,
            stream=False,
        )

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Record usage
        await usage_recorder.record(ctx, response, latency_ms, request.model)
        await session.commit()

        if response.success and response.response:
            return response.response.model_dump()

        # Return error with proper HTTP status code
        error_body = AnthropicError(
            error={"type": response.error_type, "message": response.error_message},
            request_id=ctx.request_id,
        ).model_dump()
        return JSONResponse(content=error_body, status_code=response.status_code)

    finally:
        if plan_adapter:
            await plan_adapter.close()
        await bedrock_adapter.close()


@router.post("/ak/{access_key}/v1/messages/count_tokens")
async def proxy_count_tokens(
    access_key: str,
    request: AnthropicRequest,
    raw_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    # Authenticate
    ctx = await auth_service.authenticate(access_key)
    if not ctx:
        raise HTTPException(status_code=404, detail="Not found")

    outgoing_headers = _extract_outgoing_headers(raw_request)

    # LiteLLM 방식: invalid redacted_thinking 제거 → thinking 블록 정리 → thinking param 드롭 체크
    remove_invalid_redacted_thinking(request)
    ensure_thinking_prefix(request)
    if should_drop_thinking_param(request):
        request.thinking = None

    settings = get_settings()
    has_auth_header = (
        "x-api-key" in outgoing_headers or "Authorization" in outgoing_headers
    )
    has_plan_key = bool(settings.plan_api_key)
    if not has_auth_header and not has_plan_key:
        error_body = AnthropicError(
            error={
                "type": "authentication_error",
                "message": "Missing API key for count_tokens",
            },
            request_id=ctx.request_id,
        ).model_dump()
        return JSONResponse(content=error_body, status_code=401)

    plan_adapter = PlanAdapter(headers=outgoing_headers)
    try:
        result = await plan_adapter.count_tokens(request)
        if isinstance(result, AnthropicCountTokensResponse):
            return result.model_dump()

        error_body = AnthropicError(
            error={"type": _map_error_type(result.error_type), "message": result.message},
            request_id=ctx.request_id,
        ).model_dump()
        return JSONResponse(content=error_body, status_code=result.status_code)
    finally:
        await plan_adapter.close()


@router.get("/health")
async def health():
    return {"status": "healthy"}


async def _record_streaming_usage(
    usage_recorder: UsageRecorder,
    ctx: RequestContext,
    usage: AnthropicUsage,
    latency_ms: int,
    model: str,
    is_fallback: bool,
) -> None:
    await asyncio.shield(
        usage_recorder.record_streaming_usage(
            ctx,
            usage,
            latency_ms,
            model,
            is_fallback=is_fallback,
        )
    )


def _build_bedrock_streaming_response(
    ctx: RequestContext,
    request: AnthropicRequest,
    session: AsyncSession,
    usage_aggregate_repo: UsageAggregateRepository,
    bedrock_adapter: BedrockAdapter,
    bedrock_result: AsyncIterator[bytes],
    is_fallback: bool,
) -> StreamingResponse:
    streaming_start = time.time()
    usage_recorder = UsageRecorder(
        TokenUsageRepository(session),
        usage_aggregate_repo,
        session_factory=async_session_factory,
    )
    usage_collector = StreamingUsageCollector()
    chunk_count = 0
    byte_count = 0

    async def bedrock_stream_generator():
        nonlocal chunk_count, byte_count
        try:
            async for chunk in bedrock_result:
                chunk_count += 1
                byte_count += len(chunk)
                usage_collector.feed(chunk)
                yield chunk
        except asyncio.CancelledError:
            elapsed_ms = int((time.time() - streaming_start) * 1000)
            logger.info(
                "streaming_client_disconnected",
                request_id=ctx.request_id,
                provider="bedrock",
                is_fallback=is_fallback,
                elapsed_ms=elapsed_ms,
                chunks_sent=chunk_count,
                bytes_sent=byte_count,
            )
            raise
        except Exception as exc:
            elapsed_ms = int((time.time() - streaming_start) * 1000)
            logger.warning(
                "streaming_upstream_error",
                request_id=ctx.request_id,
                provider="bedrock",
                is_fallback=is_fallback,
                elapsed_ms=elapsed_ms,
                error_type=exc.__class__.__name__,
                error=str(exc),
                is_timeout=isinstance(exc, httpx.TimeoutException),
                is_request_error=isinstance(exc, httpx.RequestError),
                chunks_sent=chunk_count,
                bytes_sent=byte_count,
            )
            raise
        finally:
            try:
                await asyncio.shield(bedrock_adapter.close())
            finally:
                usage = usage_collector.get_usage()
                if usage:
                    latency_ms = int((time.time() - streaming_start) * 1000)
                    await _record_streaming_usage(
                        usage_recorder,
                        ctx,
                        usage,
                        latency_ms,
                        request.model,
                        is_fallback,
                    )
                else:
                    logger.warning(
                        "streaming_usage_missing",
                        request_id=ctx.request_id,
                        provider="bedrock",
                        is_fallback=is_fallback,
                        elapsed_ms=int((time.time() - streaming_start) * 1000),
                        chunks_sent=chunk_count,
                        bytes_sent=byte_count,
                    )

    return StreamingResponse(
        bedrock_stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


async def _stream_plan_first(
    ctx: RequestContext,
    request: AnthropicRequest,
    session: AsyncSession,
    outgoing_headers: dict[str, str],
    budget_service: BudgetService,
    usage_aggregate_repo: UsageAggregateRepository,
):
    """Stream with Plan API first, fallback to Bedrock on retryable errors."""
    plan_adapter = PlanAdapter(headers=outgoing_headers)
    bedrock_adapter = None
    streaming_started = False
    try:
        result = await plan_adapter.stream(request)
        if isinstance(result, AdapterError):
            should_fallback = (
                ctx.has_bedrock_key
                and result.retryable
                and result.error_type in RETRYABLE_ERRORS
            )
            if should_fallback:
                budget_result = await budget_service.check_budget(
                    ctx.user_id, fail_open=False
                )
                if not budget_result.allowed:
                    error_body = AnthropicError(
                        error={
                            "type": "rate_limit_error",
                            "message": format_budget_exceeded_message(budget_result),
                        },
                        request_id=ctx.request_id,
                    ).model_dump()
                    logger.info(
                        "proxy_stream_route_result",
                        request_id=ctx.request_id,
                        provider="bedrock",
                        is_fallback=True,
                        status_code=429,
                        error_type="rate_limit_error",
                        routing_strategy=ctx.routing_strategy.value,
                    )
                    return JSONResponse(content=error_body, status_code=429)

                bedrock_adapter = BedrockAdapter(BedrockKeyRepository(session))
                bedrock_result = await bedrock_adapter.stream(ctx, request)
                if isinstance(bedrock_result, AdapterError):
                    logger.info(
                        "proxy_stream_route_result",
                        request_id=ctx.request_id,
                        provider="bedrock",
                        is_fallback=True,
                        status_code=bedrock_result.status_code,
                        error_type=_map_error_type(bedrock_result.error_type),
                        routing_strategy=ctx.routing_strategy.value,
                    )
                    error_body = AnthropicError(
                        error={
                            "type": _map_error_type(bedrock_result.error_type),
                            "message": bedrock_result.message,
                        },
                        request_id=ctx.request_id,
                    ).model_dump()
                    return JSONResponse(
                        content=error_body, status_code=bedrock_result.status_code
                    )

                streaming_started = True
                logger.info(
                    "proxy_stream_route_result",
                    request_id=ctx.request_id,
                    provider="bedrock",
                    is_fallback=True,
                    status_code=200,
                    error_type=None,
                    routing_strategy=ctx.routing_strategy.value,
                )
                return _build_bedrock_streaming_response(
                    ctx=ctx,
                    request=request,
                    session=session,
                    usage_aggregate_repo=usage_aggregate_repo,
                    bedrock_adapter=bedrock_adapter,
                    bedrock_result=bedrock_result,
                    is_fallback=True,
                )

            error_body = AnthropicError(
                error={
                    "type": _map_error_type(result.error_type),
                    "message": result.message,
                },
                request_id=ctx.request_id,
            ).model_dump()
            logger.info(
                "proxy_stream_route_result",
                request_id=ctx.request_id,
                provider="plan",
                is_fallback=False,
                status_code=result.status_code,
                error_type=_map_error_type(result.error_type),
                routing_strategy=ctx.routing_strategy.value,
            )
            return JSONResponse(content=error_body, status_code=result.status_code)

        streaming_started = True
        logger.info(
            "proxy_stream_route_result",
            request_id=ctx.request_id,
            provider="plan",
            is_fallback=False,
            status_code=200,
            error_type=None,
            routing_strategy=ctx.routing_strategy.value,
        )
        streaming_start = time.time()
        chunk_count = 0
        byte_count = 0

        async def stream_generator():
            nonlocal chunk_count, byte_count
            try:
                async for chunk in result.aiter_bytes():
                    chunk_count += 1
                    byte_count += len(chunk)
                    yield chunk
            except asyncio.CancelledError:
                elapsed_ms = int((time.time() - streaming_start) * 1000)
                logger.info(
                    "streaming_client_disconnected",
                    request_id=ctx.request_id,
                    provider="plan",
                    is_fallback=False,
                    elapsed_ms=elapsed_ms,
                    chunks_sent=chunk_count,
                    bytes_sent=byte_count,
                )
                raise
            except Exception as exc:
                elapsed_ms = int((time.time() - streaming_start) * 1000)
                logger.warning(
                    "streaming_upstream_error",
                    request_id=ctx.request_id,
                    provider="plan",
                    is_fallback=False,
                    elapsed_ms=elapsed_ms,
                    error_type=exc.__class__.__name__,
                    error=str(exc),
                    is_timeout=isinstance(exc, httpx.TimeoutException),
                    is_request_error=isinstance(exc, httpx.RequestError),
                    chunks_sent=chunk_count,
                    bytes_sent=byte_count,
                )
                raise
            finally:
                await result.aclose()
                await plan_adapter.close()

        media_type = result.headers.get("content-type", "text/event-stream")
        return StreamingResponse(
            stream_generator(),
            media_type=media_type,
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    finally:
        if not streaming_started:
            await plan_adapter.close()
            if bedrock_adapter:
                await bedrock_adapter.close()


async def _stream_bedrock_only(
    ctx: RequestContext,
    request: AnthropicRequest,
    session: AsyncSession,
    budget_service: BudgetService,
    usage_aggregate_repo: UsageAggregateRepository,
):
    """Stream directly to Bedrock, skip Plan API entirely."""
    if not ctx.has_bedrock_key:
        error_body = AnthropicError(
            error={
                "type": "api_error",
                "message": "Bedrock key not configured for bedrock_only routing",
            },
            request_id=ctx.request_id,
        ).model_dump()
        logger.info(
            "proxy_stream_route_result",
            request_id=ctx.request_id,
            provider="bedrock",
            is_fallback=False,
            status_code=503,
            error_type="api_error",
            routing_strategy=ctx.routing_strategy.value,
        )
        return JSONResponse(content=error_body, status_code=503)

    budget_result = await budget_service.check_budget(ctx.user_id, fail_open=False)
    if not budget_result.allowed:
        error_body = AnthropicError(
            error={
                "type": "rate_limit_error",
                "message": format_budget_exceeded_message(budget_result),
            },
            request_id=ctx.request_id,
        ).model_dump()
        logger.info(
            "proxy_stream_route_result",
            request_id=ctx.request_id,
            provider="bedrock",
            is_fallback=False,
            status_code=429,
            error_type="rate_limit_error",
            routing_strategy=ctx.routing_strategy.value,
        )
        return JSONResponse(content=error_body, status_code=429)

    bedrock_adapter = BedrockAdapter(BedrockKeyRepository(session))
    streaming_started = False
    try:
        bedrock_result = await bedrock_adapter.stream(ctx, request)
        if isinstance(bedrock_result, AdapterError):
            logger.info(
                "proxy_stream_route_result",
                request_id=ctx.request_id,
                provider="bedrock",
                is_fallback=False,
                status_code=bedrock_result.status_code,
                error_type=_map_error_type(bedrock_result.error_type),
                routing_strategy=ctx.routing_strategy.value,
            )
            error_body = AnthropicError(
                error={
                    "type": _map_error_type(bedrock_result.error_type),
                    "message": bedrock_result.message,
                },
                request_id=ctx.request_id,
            ).model_dump()
            return JSONResponse(
                content=error_body, status_code=bedrock_result.status_code
            )

        streaming_started = True
        logger.info(
            "proxy_stream_route_result",
            request_id=ctx.request_id,
            provider="bedrock",
            is_fallback=False,
            status_code=200,
            error_type=None,
            routing_strategy=ctx.routing_strategy.value,
        )
        return _build_bedrock_streaming_response(
            ctx=ctx,
            request=request,
            session=session,
            usage_aggregate_repo=usage_aggregate_repo,
            bedrock_adapter=bedrock_adapter,
            bedrock_result=bedrock_result,
            is_fallback=False,
        )
    finally:
        if not streaming_started:
            await bedrock_adapter.close()
