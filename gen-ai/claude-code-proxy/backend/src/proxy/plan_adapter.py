import httpx

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
            response = await self._client.post(
                url,
                json=request.model_dump(exclude_none=True, exclude={"original_model"}),
                headers=self._headers,
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                except ValueError:
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

            return self._classify_error(response.status_code, response.text)

        except (httpx.TimeoutException, httpx.RequestError) as e:
            return _handle_request_error(e, url)

    async def stream(
        self, request: AnthropicRequest, request_id: str | None = None
    ) -> httpx.Response | AdapterError:
        try:
            url = f"{self._base_url}/v1/messages"
            http_request = self._client.build_request(
                "POST",
                url,
                json=request.model_dump(exclude_none=True, exclude={"original_model"}),
                headers=self._headers,
            )
            response = await self._client.send(http_request, stream=True)

            if response.status_code == 200:
                return response

            body = await response.aread()
            await response.aclose()
            return self._classify_error(response.status_code, body.decode(errors="ignore"))

        except (httpx.TimeoutException, httpx.RequestError) as e:
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
