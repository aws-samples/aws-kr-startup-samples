import json
from typing import AsyncIterator
from uuid import UUID

import httpx

from ..config import get_settings
from ..domain import AnthropicRequest, ErrorType
from ..repositories import BedrockKeyRepository
from ..security import KMSEnvelopeEncryption
from .adapter_base import AdapterError, AdapterResponse
from .bedrock_converse import build_converse_request, iter_anthropic_sse, parse_converse_response
from .context import RequestContext
from .dependencies import get_proxy_deps


class BedrockAdapter:
    """Amazon Bedrock Converse adapter using per-user bearer token."""

    def __init__(self, bedrock_key_repo: BedrockKeyRepository):
        self._repo = bedrock_key_repo
        self._encryption = KMSEnvelopeEncryption()
        settings = get_settings()
        self._client = httpx.AsyncClient(
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
        api_key = await self._get_decrypted_key(ctx.access_key_id)
        if not api_key:
            return AdapterError(
                error_type=ErrorType.BEDROCK_AUTH_ERROR,
                status_code=401,
                message="Bedrock key not found",
                retryable=False,
            )
        try:
            payload = build_converse_request(request)
            url = _build_converse_url(ctx.bedrock_region, ctx.bedrock_model, stream=False)
            headers = _build_headers(api_key)
            response = await self._client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                return _classify_http_error(response.status_code, response.text)
            data = response.json()
            anthropic_response, usage = parse_converse_response(data, request.model)
            return AdapterResponse(response=anthropic_response, usage=usage)
        except httpx.TimeoutException:
            return AdapterError(
                error_type=ErrorType.BEDROCK_UNAVAILABLE,
                status_code=504,
                message="Request timeout",
                retryable=False,
            )
        except httpx.RequestError as exc:
            return AdapterError(
                error_type=ErrorType.BEDROCK_UNAVAILABLE,
                status_code=503,
                message=str(exc),
                retryable=False,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            return AdapterError(
                error_type=ErrorType.BEDROCK_UNAVAILABLE,
                status_code=502,
                message=f"Invalid Bedrock response: {exc}",
                retryable=False,
            )

    async def stream(
        self, ctx: RequestContext, request: AnthropicRequest
    ) -> AsyncIterator[bytes] | AdapterError:
        api_key = await self._get_decrypted_key(ctx.access_key_id)
        if not api_key:
            return AdapterError(
                error_type=ErrorType.BEDROCK_AUTH_ERROR,
                status_code=401,
                message="Bedrock key not found",
                retryable=False,
            )
        try:
            payload = build_converse_request(request)
            url = _build_converse_url(ctx.bedrock_region, ctx.bedrock_model, stream=True)
            headers = _build_headers(api_key)
            req = self._client.build_request("POST", url, json=payload, headers=headers)
            response = await self._client.send(req, stream=True)
            if response.status_code != 200:
                body = await response.aread()
                await response.aclose()
                return _classify_http_error(
                    response.status_code, body.decode(errors="ignore")
                )

            async def stream_generator():
                try:
                    async for chunk in iter_anthropic_sse(
                        response.aiter_bytes(), request.model, f"msg_{ctx.request_id}"
                    ):
                        yield chunk
                finally:
                    await response.aclose()

            return stream_generator()
        except httpx.TimeoutException:
            return AdapterError(
                error_type=ErrorType.BEDROCK_UNAVAILABLE,
                status_code=504,
                message="Request timeout",
                retryable=False,
            )
        except httpx.RequestError as exc:
            return AdapterError(
                error_type=ErrorType.BEDROCK_UNAVAILABLE,
                status_code=503,
                message=str(exc),
                retryable=False,
            )

    async def _get_decrypted_key(self, access_key_id: UUID) -> str | None:
        cache_key = str(access_key_id)
        cache = get_proxy_deps().bedrock_key_cache

        # Check cache
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Get from database and decrypt
        bedrock_key = await self._repo.get_by_access_key_id(access_key_id)
        if not bedrock_key:
            return None

        decrypted = self._encryption.decrypt(bedrock_key.encrypted_key)
        cache.set(cache_key, decrypted)
        return decrypted

    async def close(self) -> None:
        await self._client.aclose()


def _build_converse_url(region: str, model_id: str, stream: bool) -> str:
    model_id = _normalize_model_id(model_id)
    endpoint = f"https://bedrock-runtime.{region}.amazonaws.com"
    suffix = "converse-stream" if stream else "converse"
    return f"{endpoint}/model/{model_id}/{suffix}"


def _build_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _normalize_model_id(model_id: str) -> str:
    for prefix in ("bedrock/", "converse/"):
        if model_id.startswith(prefix):
            return model_id[len(prefix) :]
    return model_id


def _classify_http_error(status_code: int, body: str) -> AdapterError:
    if status_code in (401, 403):
        return AdapterError(
            error_type=ErrorType.BEDROCK_AUTH_ERROR,
            status_code=status_code,
            message="Authentication failed",
            retryable=False,
        )
    if status_code == 429:
        return AdapterError(
            error_type=ErrorType.BEDROCK_QUOTA_EXCEEDED,
            status_code=status_code,
            message="Quota exceeded",
            retryable=False,
        )
    if status_code in (400, 422):
        return AdapterError(
            error_type=ErrorType.BEDROCK_VALIDATION,
            status_code=status_code,
            message=body[:200],
            retryable=False,
        )
    return AdapterError(
        error_type=ErrorType.BEDROCK_UNAVAILABLE,
        status_code=status_code,
        message=body[:200],
        retryable=False,
    )


def invalidate_bedrock_key_cache(access_key_id: UUID) -> None:
    get_proxy_deps().bedrock_key_cache.invalidate(str(access_key_id))
