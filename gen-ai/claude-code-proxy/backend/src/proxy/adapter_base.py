from dataclasses import dataclass
from typing import Protocol

from ..domain import AnthropicRequest, AnthropicResponse, AnthropicUsage, ErrorType
from .context import RequestContext


@dataclass
class AdapterResponse:
    """Successful adapter response."""

    response: AnthropicResponse
    usage: AnthropicUsage


@dataclass
class AdapterError:
    """Adapter error with classification."""

    error_type: ErrorType
    status_code: int
    message: str
    retryable: bool


class Adapter(Protocol):
    """Protocol for upstream adapters."""

    async def invoke(
        self, ctx: RequestContext, request: AnthropicRequest
    ) -> AdapterResponse | AdapterError:
        ...
