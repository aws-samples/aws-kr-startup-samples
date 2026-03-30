import json
from typing import AsyncIterator

import boto3
from botocore.config import Config as BotoConfig

from ..config import get_settings
from ..domain import AnthropicRequest, ErrorType
from .adapter_base import AdapterError, AdapterResponse
from .bedrock_converse import build_converse_request, parse_converse_response
from .context import RequestContext
from .dependencies import get_proxy_deps


class BedrockAdapter:
    """Amazon Bedrock Converse adapter using IAM role (ECS task role)."""

    def __init__(self):
        settings = get_settings()
        self._region = settings.bedrock_region
        self._boto_config = BotoConfig(
            region_name=self._region,
            connect_timeout=int(settings.http_connect_timeout),
            read_timeout=int(settings.http_read_timeout),
            retries={"max_attempts": 0},
        )

    def _get_client(self, region: str | None = None):
        r = region or self._region
        cfg = BotoConfig(
            region_name=r,
            connect_timeout=self._boto_config.connect_timeout,
            read_timeout=self._boto_config.read_timeout,
            retries={"max_attempts": 0},
        )
        return boto3.client("bedrock-runtime", config=cfg)

    async def invoke(
        self, ctx: RequestContext, request: AnthropicRequest
    ) -> AdapterResponse | AdapterError:
        resolved_model = get_proxy_deps().bedrock_model_resolver.resolve(request.model)
        payload = build_converse_request(
            request,
            caching_strategy=ctx.caching_strategy,
            model_id=resolved_model,
        )
        region = ctx.bedrock_region or self._region
        try:
            client = self._get_client(region)
            model_id = _normalize_model_id(resolved_model)
            response = client.converse(modelId=model_id, **payload)
            anthropic_response, usage = parse_converse_response(response, request.model)
            return AdapterResponse(response=anthropic_response, usage=usage)
        except client.exceptions.ThrottlingException:
            return AdapterError(
                error_type=ErrorType.BEDROCK_QUOTA_EXCEEDED,
                status_code=429,
                message="Quota exceeded",
                retryable=False,
            )
        except client.exceptions.AccessDeniedException as exc:
            return AdapterError(
                error_type=ErrorType.BEDROCK_AUTH_ERROR,
                status_code=403,
                message=str(exc),
                retryable=False,
            )
        except client.exceptions.ValidationException as exc:
            return AdapterError(
                error_type=ErrorType.BEDROCK_VALIDATION,
                status_code=400,
                message=str(exc)[:200],
                retryable=False,
            )
        except Exception as exc:
            return AdapterError(
                error_type=ErrorType.BEDROCK_UNAVAILABLE,
                status_code=503,
                message=str(exc)[:200],
                retryable=False,
            )

    async def stream(
        self, ctx: RequestContext, request: AnthropicRequest
    ) -> AsyncIterator[bytes] | AdapterError:
        resolved_model = get_proxy_deps().bedrock_model_resolver.resolve(request.model)
        payload = build_converse_request(
            request,
            caching_strategy=ctx.caching_strategy,
            model_id=resolved_model,
        )
        region = ctx.bedrock_region or self._region
        try:
            client = self._get_client(region)
            model_id = _normalize_model_id(resolved_model)
            response = client.converse_stream(modelId=model_id, **payload)
            event_stream = response.get("stream")
            if not event_stream:
                return AdapterError(
                    error_type=ErrorType.BEDROCK_UNAVAILABLE,
                    status_code=502,
                    message="No stream in response",
                    retryable=False,
                )

            async def stream_generator():
                for event in event_stream:
                    yield _event_to_sse(event)

            return stream_generator()
        except Exception as exc:
            return AdapterError(
                error_type=ErrorType.BEDROCK_UNAVAILABLE,
                status_code=503,
                message=str(exc)[:200],
                retryable=False,
            )

    async def close(self) -> None:
        pass


def _normalize_model_id(model_id: str) -> str:
    for prefix in ("bedrock/", "converse/"):
        if model_id.startswith(prefix):
            return model_id[len(prefix):]
    return model_id


def _event_to_sse(event: dict) -> bytes:
    data = json.dumps(event)
    return f"data: {data}\n\n".encode()
