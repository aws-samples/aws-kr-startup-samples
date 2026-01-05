"""
BedrockAdapter unit tests.

Tests cover:
- HTTP error classification
- URL building and model ID normalization
- invoke() success and failure paths
- stream() success and failure paths
- Decrypted key caching behavior
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from src.domain import AnthropicRequest, AnthropicResponse, AnthropicUsage, ErrorType
from src.proxy.bedrock_adapter import (
    BedrockAdapter,
    _build_converse_url,
    _classify_http_error,
    _normalize_model_id,
)
from src.proxy.context import RequestContext


# =============================================================================
# _classify_http_error tests
# =============================================================================


@pytest.mark.parametrize(
    "status_code,expected_type",
    [
        (401, ErrorType.BEDROCK_AUTH_ERROR),
        (403, ErrorType.BEDROCK_AUTH_ERROR),
        (429, ErrorType.BEDROCK_QUOTA_EXCEEDED),
        (400, ErrorType.BEDROCK_VALIDATION),
        (422, ErrorType.BEDROCK_VALIDATION),
        (500, ErrorType.BEDROCK_UNAVAILABLE),
        (502, ErrorType.BEDROCK_UNAVAILABLE),
        (503, ErrorType.BEDROCK_UNAVAILABLE),
        (504, ErrorType.BEDROCK_UNAVAILABLE),
    ],
)
def test_classify_http_error_maps_status_codes(status_code: int, expected_type: ErrorType):
    error = _classify_http_error(status_code, "error body")
    assert error.error_type == expected_type
    assert error.status_code == status_code
    assert error.retryable is False


def test_classify_http_error_truncates_long_body():
    long_body = "x" * 500
    error = _classify_http_error(500, long_body)
    assert len(error.message) == 200


def test_classify_http_error_auth_message():
    error = _classify_http_error(401, "some detail")
    assert error.message == "Authentication failed"


def test_classify_http_error_quota_message():
    error = _classify_http_error(429, "throttled")
    assert error.message == "Quota exceeded"


# =============================================================================
# _normalize_model_id tests
# =============================================================================


@pytest.mark.parametrize(
    "input_id,expected",
    [
        ("bedrock/claude-3-sonnet", "claude-3-sonnet"),
        ("converse/claude-3-opus", "claude-3-opus"),
        ("claude-3-haiku", "claude-3-haiku"),
        ("anthropic.claude-v2", "anthropic.claude-v2"),
        ("bedrock/", ""),
        ("converse/", ""),
    ],
)
def test_normalize_model_id(input_id: str, expected: str):
    assert _normalize_model_id(input_id) == expected


def test_normalize_model_id_only_strips_first_prefix():
    # "bedrock/bedrock/model" should become "bedrock/model"
    result = _normalize_model_id("bedrock/bedrock/model")
    assert result == "bedrock/model"


# =============================================================================
# _build_converse_url tests
# =============================================================================


def test_build_converse_url_non_stream():
    url = _build_converse_url("us-east-1", "claude-3-sonnet", stream=False)
    assert url == "https://bedrock-runtime.us-east-1.amazonaws.com/model/claude-3-sonnet/converse"


def test_build_converse_url_stream():
    url = _build_converse_url("ap-northeast-2", "claude-3-opus", stream=True)
    assert (
        url
        == "https://bedrock-runtime.ap-northeast-2.amazonaws.com/model/claude-3-opus/converse-stream"
    )


def test_build_converse_url_normalizes_model_id():
    url = _build_converse_url("us-west-2", "bedrock/claude-3", stream=False)
    assert "model/claude-3/converse" in url
    assert "bedrock/" not in url


# =============================================================================
# BedrockAdapter.invoke() tests
# =============================================================================


def _make_context(**overrides) -> RequestContext:
    defaults = {
        "request_id": "req_test123",
        "user_id": uuid4(),
        "access_key_id": uuid4(),
        "access_key_prefix": "ak_test",
        "bedrock_region": "ap-northeast-2",
        "bedrock_model": "claude-3-sonnet",
        "has_bedrock_key": True,
    }
    defaults.update(overrides)
    return RequestContext(**defaults)


def _make_request(**overrides) -> AnthropicRequest:
    defaults = {
        "model": "claude-3-sonnet",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    defaults.update(overrides)
    return AnthropicRequest(**defaults)


@pytest.mark.asyncio
async def test_invoke_returns_auth_error_when_key_not_found():
    mock_repo = AsyncMock()
    adapter = BedrockAdapter(mock_repo)

    with patch.object(adapter, "_get_decrypted_key", return_value=None):
        ctx = _make_context()
        request = _make_request()

        result = await adapter.invoke(ctx, request)

        assert result.error_type == ErrorType.BEDROCK_AUTH_ERROR
        assert result.status_code == 401
        assert "not found" in result.message

    await adapter.close()


@pytest.mark.asyncio
async def test_invoke_success_returns_response_and_usage():
    mock_repo = AsyncMock()
    adapter = BedrockAdapter(mock_repo)

    mock_response_data = {
        "id": "resp_123",
        "stopReason": "end_turn",
        "usage": {"inputTokens": 10, "outputTokens": 20},
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "Hello!"}],
            }
        },
    }

    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = mock_response_data

    with (
        patch.object(adapter, "_get_decrypted_key", return_value="fake-api-key"),
        patch.object(adapter._client, "post", return_value=mock_http_response),
    ):
        ctx = _make_context()
        request = _make_request()

        result = await adapter.invoke(ctx, request)

        assert result.response is not None
        assert result.usage is not None
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 20

    await adapter.close()


@pytest.mark.asyncio
async def test_invoke_http_error_returns_classified_error():
    mock_repo = AsyncMock()
    adapter = BedrockAdapter(mock_repo)

    mock_http_response = MagicMock()
    mock_http_response.status_code = 429
    mock_http_response.text = "Rate limited"

    with (
        patch.object(adapter, "_get_decrypted_key", return_value="fake-api-key"),
        patch.object(adapter._client, "post", return_value=mock_http_response),
    ):
        ctx = _make_context()
        request = _make_request()

        result = await adapter.invoke(ctx, request)

        assert result.error_type == ErrorType.BEDROCK_QUOTA_EXCEEDED
        assert result.status_code == 429

    await adapter.close()


@pytest.mark.asyncio
async def test_invoke_timeout_returns_504():
    mock_repo = AsyncMock()
    adapter = BedrockAdapter(mock_repo)

    with (
        patch.object(adapter, "_get_decrypted_key", return_value="fake-api-key"),
        patch.object(adapter._client, "post", side_effect=httpx.TimeoutException("timeout")),
    ):
        ctx = _make_context()
        request = _make_request()

        result = await adapter.invoke(ctx, request)

        assert result.error_type == ErrorType.BEDROCK_UNAVAILABLE
        assert result.status_code == 504
        assert "timeout" in result.message.lower()

    await adapter.close()


@pytest.mark.asyncio
async def test_invoke_network_error_returns_503():
    mock_repo = AsyncMock()
    adapter = BedrockAdapter(mock_repo)

    with (
        patch.object(adapter, "_get_decrypted_key", return_value="fake-api-key"),
        patch.object(
            adapter._client, "post", side_effect=httpx.RequestError("connection failed")
        ),
    ):
        ctx = _make_context()
        request = _make_request()

        result = await adapter.invoke(ctx, request)

        assert result.error_type == ErrorType.BEDROCK_UNAVAILABLE
        assert result.status_code == 503

    await adapter.close()


@pytest.mark.asyncio
async def test_invoke_invalid_json_returns_502():
    mock_repo = AsyncMock()
    adapter = BedrockAdapter(mock_repo)

    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.json.side_effect = ValueError("invalid json")

    with (
        patch.object(adapter, "_get_decrypted_key", return_value="fake-api-key"),
        patch.object(adapter._client, "post", return_value=mock_http_response),
    ):
        ctx = _make_context()
        request = _make_request()

        result = await adapter.invoke(ctx, request)

        assert result.error_type == ErrorType.BEDROCK_UNAVAILABLE
        assert result.status_code == 502
        assert "Invalid Bedrock response" in result.message

    await adapter.close()


# =============================================================================
# BedrockAdapter.stream() tests
# =============================================================================


@pytest.mark.asyncio
async def test_stream_returns_auth_error_when_key_not_found():
    mock_repo = AsyncMock()
    adapter = BedrockAdapter(mock_repo)

    with patch.object(adapter, "_get_decrypted_key", return_value=None):
        ctx = _make_context()
        request = _make_request(stream=True)

        result = await adapter.stream(ctx, request)

        assert result.error_type == ErrorType.BEDROCK_AUTH_ERROR
        assert result.status_code == 401

    await adapter.close()


@pytest.mark.asyncio
async def test_stream_http_error_returns_classified_error():
    mock_repo = AsyncMock()
    adapter = BedrockAdapter(mock_repo)

    mock_http_response = AsyncMock()
    mock_http_response.status_code = 403
    mock_http_response.aread = AsyncMock(return_value=b"Forbidden")
    mock_http_response.aclose = AsyncMock()

    with (
        patch.object(adapter, "_get_decrypted_key", return_value="fake-api-key"),
        patch.object(adapter._client, "build_request", return_value=MagicMock()),
        patch.object(adapter._client, "send", return_value=mock_http_response),
    ):
        ctx = _make_context()
        request = _make_request(stream=True)

        result = await adapter.stream(ctx, request)

        assert result.error_type == ErrorType.BEDROCK_AUTH_ERROR
        assert result.status_code == 403
        mock_http_response.aclose.assert_called_once()

    await adapter.close()


@pytest.mark.asyncio
async def test_stream_timeout_returns_504():
    mock_repo = AsyncMock()
    adapter = BedrockAdapter(mock_repo)

    with (
        patch.object(adapter, "_get_decrypted_key", return_value="fake-api-key"),
        patch.object(adapter._client, "build_request", return_value=MagicMock()),
        patch.object(adapter._client, "send", side_effect=httpx.TimeoutException("timeout")),
    ):
        ctx = _make_context()
        request = _make_request(stream=True)

        result = await adapter.stream(ctx, request)

        assert result.error_type == ErrorType.BEDROCK_UNAVAILABLE
        assert result.status_code == 504

    await adapter.close()


# =============================================================================
# BedrockAdapter._get_decrypted_key() cache tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_decrypted_key_caches_result():
    mock_repo = AsyncMock()
    mock_bedrock_key = MagicMock()
    mock_bedrock_key.encrypted_key = b"encrypted"
    mock_repo.get_by_access_key_id = AsyncMock(return_value=mock_bedrock_key)

    adapter = BedrockAdapter(mock_repo)
    access_key_id = uuid4()

    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    with (
        patch("src.proxy.bedrock_adapter.get_proxy_deps") as mock_deps,
        patch.object(adapter._encryption, "decrypt", return_value="decrypted-key"),
    ):
        mock_deps.return_value.bedrock_key_cache = mock_cache

        # First call - should query DB
        result1 = await adapter._get_decrypted_key(access_key_id)

        assert result1 == "decrypted-key"
        mock_repo.get_by_access_key_id.assert_called_once_with(access_key_id)
        mock_cache.set.assert_called_once()

    await adapter.close()


@pytest.mark.asyncio
async def test_get_decrypted_key_returns_cached_value():
    mock_repo = AsyncMock()
    adapter = BedrockAdapter(mock_repo)
    access_key_id = uuid4()

    mock_cache = MagicMock()
    mock_cache.get.return_value = "cached-key"

    with patch("src.proxy.bedrock_adapter.get_proxy_deps") as mock_deps:
        mock_deps.return_value.bedrock_key_cache = mock_cache

        result = await adapter._get_decrypted_key(access_key_id)

        assert result == "cached-key"
        mock_repo.get_by_access_key_id.assert_not_called()

    await adapter.close()


@pytest.mark.asyncio
async def test_get_decrypted_key_returns_none_when_not_in_db():
    mock_repo = AsyncMock()
    mock_repo.get_by_access_key_id = AsyncMock(return_value=None)

    adapter = BedrockAdapter(mock_repo)
    access_key_id = uuid4()

    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    with patch("src.proxy.bedrock_adapter.get_proxy_deps") as mock_deps:
        mock_deps.return_value.bedrock_key_cache = mock_cache

        result = await adapter._get_decrypted_key(access_key_id)

        assert result is None
        mock_cache.set.assert_not_called()

    await adapter.close()
