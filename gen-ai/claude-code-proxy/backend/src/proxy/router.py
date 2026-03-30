from dataclasses import dataclass
from collections.abc import Awaitable, Callable

from ..domain import (
    AnthropicRequest,
    AnthropicResponse,
    AnthropicUsage,
    Provider,
    ErrorType,
)
from .context import RequestContext
from .budget import BudgetCheckResult, format_budget_exceeded_message
from .adapter_base import AdapterResponse, AdapterError, Adapter


# Map internal error types to Anthropic API error types
ANTHROPIC_ERROR_TYPE_MAP = {
    ErrorType.RATE_LIMIT: "rate_limit_error",
    ErrorType.USAGE_LIMIT: "rate_limit_error",
    ErrorType.SERVER_ERROR: "api_error",
    ErrorType.CLIENT_ERROR: "invalid_request_error",
    ErrorType.TIMEOUT: "overloaded_error",
    ErrorType.NETWORK_ERROR: "api_error",
    ErrorType.BEDROCK_AUTH_ERROR: "authentication_error",
    ErrorType.BEDROCK_QUOTA_EXCEEDED: "rate_limit_error",
    ErrorType.BEDROCK_VALIDATION: "invalid_request_error",
    ErrorType.BEDROCK_MODEL_ERROR: "api_error",
    ErrorType.BEDROCK_UNAVAILABLE: "overloaded_error",
}


def _map_error_type(error_type: ErrorType) -> str:
    return ANTHROPIC_ERROR_TYPE_MAP.get(error_type, "api_error")


@dataclass
class ProxyResponse:
    """Final proxy response."""

    success: bool
    response: AnthropicResponse | None
    usage: AnthropicUsage | None
    provider: Provider
    is_fallback: bool
    status_code: int
    error_type: str | None = None
    error_message: str | None = None
    fallback_reason: str | None = None


class ProxyRouter:
    """Routes requests to Bedrock."""

    def __init__(
        self,
        bedrock_adapter: Adapter,
        budget_checker: Callable[[RequestContext], Awaitable[BudgetCheckResult]] | None = None,
    ):
        self._bedrock = bedrock_adapter
        self._budget_checker = budget_checker

    async def route(self, ctx: RequestContext, request: AnthropicRequest) -> ProxyResponse:
        if self._budget_checker:
            budget_result = await self._budget_checker(ctx)
            if not budget_result.allowed:
                return ProxyResponse(
                    success=False, response=None, usage=None, provider="bedrock",
                    is_fallback=False, status_code=429,
                    error_type="rate_limit_error",
                    error_message=format_budget_exceeded_message(budget_result),
                )

        result = await self._bedrock.invoke(ctx, request)

        if isinstance(result, AdapterResponse):
            return ProxyResponse(
                success=True, response=result.response, usage=result.usage,
                provider="bedrock", is_fallback=False, status_code=200,
            )

        return ProxyResponse(
            success=False, response=None, usage=None, provider="bedrock",
            is_fallback=False, status_code=result.status_code,
            error_type=_map_error_type(result.error_type), error_message=result.message,
        )
