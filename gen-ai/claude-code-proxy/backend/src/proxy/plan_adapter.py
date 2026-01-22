import httpx
import structlog

from ..domain import (
    AnthropicRequest,
    AnthropicResponse,
    AnthropicUsage,
    AnthropicCountTokensResponse,
    ErrorType,
)
from ..config import get_settings
from .context import RequestContext
from .adapter_base import AdapterResponse, AdapterError

logger = structlog.get_logger(__name__)


def _handle_request_error(e: Exception, url: str) -> AdapterError:
    """Convert httpx exceptions to AdapterError."""
    if isinstance(e, httpx.TimeoutException):
        return AdapterError(ErrorType.TIMEOUT, 504, "Request timeout", True)
    return AdapterError(ErrorType.NETWORK_ERROR, 503, str(e), True)


class PlanAdapter:
    """Anthropic Plan API adapter."""

    def __init__(self, api_key: str | None = None, headers: dict | None = None):
        settings = get_settings()
        self._api_key = api_key or settings.plan_api_key
        self._base_url = settings.plan_api_url
        self._headers = headers.copy() if headers else {}
        if (
            self._api_key
            and "authorization" not in {k.lower() for k in self._headers}
            and "x-api-key" not in {k.lower() for k in self._headers}
        ):
            self._headers["x-api-key"] = self._api_key
        if "anthropic-version" not in {k.lower() for k in self._headers}:
            self._headers["anthropic-version"] = "2023-06-01"
        if "content-type" not in {k.lower() for k in self._headers}:
            self._headers["content-type"] = "application/json"
        verify: bool | str = True
        if settings.plan_ca_bundle:
            verify = settings.plan_ca_bundle
        elif not settings.plan_verify_ssl:
            verify = False
        self._client = httpx.AsyncClient(
            verify=verify,
            timeout=httpx.Timeout(
                connect=settings.http_connect_timeout,
                read=settings.http_read_timeout,
                write=30.0,
                pool=10.0,
            )
        )

    async def invoke(
        self, ctx: RequestContext, request: AnthropicRequest
    ) -> AdapterResponse | AdapterError:
        try:
            url = f"{self._base_url}/v1/messages"
            request_payload = request.model_dump(exclude_none=True, exclude={"original_model"})
            
            logger.info(
                "plan_api_request",
                request_id=ctx.request_id,
                user_id=ctx.user_id,
                access_key_id=ctx.access_key_id,
                model=request.model,
                max_tokens=request.max_tokens,
                stream=request.stream,
                url=url,
            )
            
            response = await self._client.post(
                url,
                json=request_payload,
                headers=self._headers,
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    usage_data = data.get("usage", {})
                    
                    logger.info(
                        "plan_api_response_success",
                        request_id=ctx.request_id,
                        user_id=ctx.user_id,
                        access_key_id=ctx.access_key_id,
                        model=request.model,
                        response_model=data.get("model"),
                        input_tokens=usage_data.get("input_tokens", 0),
                        output_tokens=usage_data.get("output_tokens", 0),
                        cache_creation_input_tokens=usage_data.get("cache_creation_input_tokens", 0),
                        cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
                        stop_reason=data.get("stop_reason"),
                    )
                except ValueError:
                    logger.error(
                        "plan_api_invalid_json",
                        request_id=ctx.request_id,
                        status_code=response.status_code,
                    )
                    return AdapterError(
                        error_type=ErrorType.SERVER_ERROR,
                        status_code=502,
                        message="Upstream returned invalid JSON",
                        retryable=True,
                    )
                return AdapterResponse(
                    response=AnthropicResponse(**data),
                    usage=AnthropicUsage(**data.get("usage", {})),
                )

            logger.warning(
                "plan_api_response_error",
                request_id=ctx.request_id,
                user_id=ctx.user_id,
                status_code=response.status_code,
                response_text=response.text[:500],
            )
            return self._classify_error(response.status_code, response.text)

        except (httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(
                "plan_api_request_error",
                request_id=ctx.request_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return _handle_request_error(e, url)

    async def stream(
        self, request: AnthropicRequest, request_id: str | None = None
    ) -> httpx.Response | AdapterError:
        try:
            url = f"{self._base_url}/v1/messages"
            request_payload = request.model_dump(exclude_none=True, exclude={"original_model"})
            
            logger.info(
                "plan_api_stream_request",
                request_id=request_id,
                model=request.model,
                max_tokens=request.max_tokens,
                stream=request.stream,
                url=url,
            )
            
            http_request = self._client.build_request(
                "POST",
                url,
                json=request_payload,
                headers=self._headers,
            )
            response = await self._client.send(http_request, stream=True)

            if response.status_code == 200:
                logger.info(
                    "plan_api_stream_response_started",
                    request_id=request_id,
                    model=request.model,
                    status_code=response.status_code,
                )
                return response

            body = await response.aread()
            await response.aclose()
            
            logger.warning(
                "plan_api_stream_error",
                request_id=request_id,
                status_code=response.status_code,
                response_text=body.decode(errors="ignore")[:500],
            )
            return self._classify_error(response.status_code, body.decode(errors="ignore"))

        except (httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(
                "plan_api_stream_request_error",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return _handle_request_error(e, url)

    async def count_tokens(
        self, request: AnthropicRequest, request_id: str | None = None
    ) -> AnthropicCountTokensResponse | AdapterError:
        try:
            url = f"{self._base_url}/v1/messages/count_tokens"
            response = await self._client.post(
                url,
                json=request.model_dump(exclude_none=True, exclude={"original_model"}),
                headers=self._headers,
            )

            if response.status_code == 200:
                result = AnthropicCountTokensResponse(**response.json())
                return result

            return self._classify_error(response.status_code, response.text)

        except (httpx.TimeoutException, httpx.RequestError) as e:
            return _handle_request_error(e, url)

    def _classify_error(self, status_code: int, body: str) -> AdapterError:
        if status_code == 429:
            # Check if usage limit vs rate limit
            if "usage" in body.lower():
                return AdapterError(
                    error_type=ErrorType.USAGE_LIMIT,
                    status_code=429,
                    message="Usage limit exceeded",
                    retryable=True,
                )
            return AdapterError(
                error_type=ErrorType.RATE_LIMIT,
                status_code=429,
                message="Rate limit exceeded",
                retryable=True,
            )
        if 500 <= status_code < 600:
            return AdapterError(
                error_type=ErrorType.SERVER_ERROR,
                status_code=status_code,
                message="Server error",
                retryable=True,
            )
        return AdapterError(
            error_type=ErrorType.CLIENT_ERROR,
            status_code=status_code,
            message=body[:200],
            retryable=False,
        )

    async def close(self) -> None:
        await self._client.aclose()
