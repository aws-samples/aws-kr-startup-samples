import asyncio
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session, async_session_factory
from ..config import get_settings
from ..domain import AnthropicRequest, AnthropicError, AnthropicCountTokensResponse, RETRYABLE_ERRORS, RoutingStrategy
from ..logging import get_logger
from ..repositories import (
    BedrockKeyRepository,
    TokenUsageRepository,
    UsageAggregateRepository,
    UserRepository,
)
from ..proxy import (
    AuthService,
    get_auth_service,
    ProxyRouter,
    PlanAdapter,
    BedrockAdapter,
    UsageRecorder,
    BudgetService,
)
from ..proxy.budget import format_budget_exceeded_message
from ..proxy.adapter_base import AdapterError
from ..proxy.router import _map_error_type
from ..proxy.streaming_usage import StreamingUsageCollector

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

    # Log header presence (do not log secrets)
    logger.info(
        "proxy_auth_headers",
        has_x_api_key="x-api-key" in outgoing_headers,
        has_authorization="Authorization" in outgoing_headers,
        authorization_is_bearer=outgoing_headers.get("Authorization", "").startswith("Bearer "),
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

    plan_adapter = PlanAdapter(headers=outgoing_headers)
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


async def _stream_plan_first(
    ctx,
    request: AnthropicRequest,
    session: AsyncSession,
    outgoing_headers: dict[str, str],
    budget_service: BudgetService,
    usage_aggregate_repo: UsageAggregateRepository,
):
    """Stream with Plan API first, fallback to Bedrock on retryable errors."""
    from ..proxy.context import RequestContext

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
                    return JSONResponse(content=error_body, status_code=429)

                bedrock_adapter = BedrockAdapter(BedrockKeyRepository(session))
                bedrock_result = await bedrock_adapter.stream(ctx, request)
                if isinstance(bedrock_result, AdapterError):
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
                streaming_start = time.time()
                usage_recorder = UsageRecorder(
                    TokenUsageRepository(session),
                    usage_aggregate_repo,
                    session_factory=async_session_factory,
                )
                usage_collector = StreamingUsageCollector()

                async def bedrock_stream_generator():
                    try:
                        async for chunk in bedrock_result:
                            usage_collector.feed(chunk)
                            yield chunk
                    finally:
                        await bedrock_adapter.close()
                        usage = usage_collector.get_usage()
                        if usage:
                            latency_ms = int((time.time() - streaming_start) * 1000)
                            asyncio.create_task(
                                usage_recorder.record_streaming_usage(
                                    ctx,
                                    usage,
                                    latency_ms,
                                    request.model,
                                    is_fallback=True,
                                )
                            )
                        else:
                            logger.warning(
                                "streaming_usage_missing",
                                request_id=ctx.request_id,
                                provider="bedrock",
                            )

                return StreamingResponse(
                    bedrock_stream_generator(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )

            error_body = AnthropicError(
                error={
                    "type": _map_error_type(result.error_type),
                    "message": result.message,
                },
                request_id=ctx.request_id,
            ).model_dump()
            return JSONResponse(content=error_body, status_code=result.status_code)

        streaming_started = True

        async def stream_generator():
            try:
                async for chunk in result.aiter_bytes():
                    yield chunk
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
    ctx,
    request: AnthropicRequest,
    session: AsyncSession,
    budget_service: BudgetService,
    usage_aggregate_repo: UsageAggregateRepository,
):
    """Stream directly to Bedrock, skip Plan API entirely."""
    logger.info(
        "streaming_bedrock_only",
        user_id=str(ctx.user_id),
        access_key_id=str(ctx.access_key_id),
    )

    if not ctx.has_bedrock_key:
        error_body = AnthropicError(
            error={
                "type": "api_error",
                "message": "Bedrock key not configured for bedrock_only routing",
            },
            request_id=ctx.request_id,
        ).model_dump()
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
        return JSONResponse(content=error_body, status_code=429)

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
            return JSONResponse(
                content=error_body, status_code=bedrock_result.status_code
            )

        streaming_started = True
        streaming_start = time.time()
        usage_recorder = UsageRecorder(
            TokenUsageRepository(session),
            usage_aggregate_repo,
            session_factory=async_session_factory,
        )
        usage_collector = StreamingUsageCollector()

        async def bedrock_stream_generator():
            try:
                async for chunk in bedrock_result:
                    usage_collector.feed(chunk)
                    yield chunk
            finally:
                await bedrock_adapter.close()
                usage = usage_collector.get_usage()
                if usage:
                    latency_ms = int((time.time() - streaming_start) * 1000)
                    asyncio.create_task(
                        usage_recorder.record_streaming_usage(
                            ctx,
                            usage,
                            latency_ms,
                            request.model,
                            is_fallback=False,
                        )
                    )
                else:
                    logger.warning(
                        "streaming_usage_missing",
                        request_id=ctx.request_id,
                        provider="bedrock",
                    )

        return StreamingResponse(
            bedrock_stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    finally:
        if not streaming_started:
            await bedrock_adapter.close()
