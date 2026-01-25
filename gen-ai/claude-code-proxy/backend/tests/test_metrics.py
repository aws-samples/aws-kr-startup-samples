"""Tests for CloudWatch, OTEL, and Composite metrics emitters."""

from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.proxy.metrics import (
    CloudWatchMetricsEmitter,
    CompositeMetricsEmitter,
    OTELMetricsEmitter,
    _normalize_model,
    get_default_metrics_emitter,
)


@dataclass
class _MinimalUsage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None


@dataclass
class _MinimalResponse:
    provider: str
    error_type: str | None
    is_fallback: bool
    usage: object | None


@patch("src.proxy.metrics.boto3")
def test_emit_sync_proxy_requests_latency_cost(mock_boto3: MagicMock) -> None:
    mock_cw = MagicMock()
    mock_boto3.client.return_value = mock_cw

    with patch("src.proxy.metrics.get_settings") as m:
        m.return_value.cloudwatch_namespace = "TestNS"
        m.return_value.bedrock_region = "us-east-1"
        m.return_value.cloudwatch_metrics_enabled = True

        emitter = CloudWatchMetricsEmitter(namespace="TestNS", region="us-east-1")
        resp = _MinimalResponse(provider="bedrock", error_type=None, is_fallback=False, usage=None)
        emitter._emit_sync(
            resp, 100, "anthropic.claude-sonnet-4-5-20250514", Decimal("0.001"), False, None, None
        )

    mock_cw.put_metric_data.assert_called_once()
    call = mock_cw.put_metric_data.call_args
    assert call.kwargs["Namespace"] == "TestNS"
    metrics = {m["MetricName"]: m for m in call.kwargs["MetricData"]}
    assert "proxy.requests" in metrics
    assert metrics["proxy.requests"]["Value"] == 1
    dims = {d["Name"]: d["Value"] for d in metrics["proxy.requests"]["Dimensions"]}
    assert dims["Provider"] == "bedrock"
    assert dims["Model"] == "claude-sonnet-4-5"
    assert dims["Status"] == "success"
    assert dims["Stream"] == "false"
    assert "proxy.latency" in metrics
    assert metrics["proxy.latency"]["Value"] == 100
    assert "proxy.cost" in metrics
    assert metrics["proxy.cost"]["Value"] == 0.001


@patch("src.proxy.metrics.boto3")
def test_emit_sync_proxy_tokens_when_usage(mock_boto3: MagicMock) -> None:
    mock_cw = MagicMock()
    mock_boto3.client.return_value = mock_cw

    with patch("src.proxy.metrics.get_settings") as m:
        m.return_value.cloudwatch_namespace = "TestNS"
        m.return_value.bedrock_region = "us-east-1"
        m.return_value.cloudwatch_metrics_enabled = True

        emitter = CloudWatchMetricsEmitter(namespace="TestNS", region="us-east-1")
        usage = _MinimalUsage(10, 5, 1, 2)
        resp = _MinimalResponse(provider="plan", error_type=None, is_fallback=False, usage=usage)
        emitter._emit_sync(resp, 50, "claude-opus", Decimal("0"), False, None, None)

    data = mock_cw.put_metric_data.call_args.kwargs["MetricData"]
    token_entries = [m for m in data if m["MetricName"] == "proxy.tokens"]
    assert len(token_entries) == 4
    by_type = {d["Dimensions"][-1]["Value"]: d["Value"] for d in token_entries}
    assert by_type["input"] == 10
    assert by_type["output"] == 5
    assert by_type["cache_read"] == 1
    assert by_type["cache_write"] == 2


@patch("src.proxy.metrics.boto3")
def test_emit_sync_proxy_errors_fallbacks(mock_boto3: MagicMock) -> None:
    mock_cw = MagicMock()
    mock_boto3.client.return_value = mock_cw

    with patch("src.proxy.metrics.get_settings") as m:
        m.return_value.cloudwatch_namespace = "TestNS"
        m.return_value.bedrock_region = "us-east-1"
        m.return_value.cloudwatch_metrics_enabled = True

        emitter = CloudWatchMetricsEmitter(namespace="TestNS", region="us-east-1")
        resp = _MinimalResponse(
            provider="bedrock", error_type="rate_limit_error", is_fallback=True, usage=None
        )
        emitter._emit_sync(resp, 200, "x", Decimal("0"), False, None, "rate_limit_error")

    metrics = {m["MetricName"]: m for m in mock_cw.put_metric_data.call_args.kwargs["MetricData"]}
    assert "proxy.errors" in metrics
    assert metrics["proxy.errors"]["Dimensions"] == [
        {"Name": "Provider", "Value": "bedrock"},
        {"Name": "ErrorType", "Value": "rate_limit_error"},
    ]
    assert "proxy.fallbacks" in metrics
    assert metrics["proxy.fallbacks"]["Dimensions"] == [
        {"Name": "FromProvider", "Value": "plan"},
        {"Name": "ToProvider", "Value": "bedrock"},
        {"Name": "Reason", "Value": "rate_limit_error"},
    ]


@patch("src.proxy.metrics.boto3")
def test_emit_sync_proxy_ttft_when_ttft_ms(mock_boto3: MagicMock) -> None:
    mock_cw = MagicMock()
    mock_boto3.client.return_value = mock_cw

    with patch("src.proxy.metrics.get_settings") as m:
        m.return_value.cloudwatch_namespace = "TestNS"
        m.return_value.bedrock_region = "us-east-1"
        m.return_value.cloudwatch_metrics_enabled = True

        emitter = CloudWatchMetricsEmitter(namespace="TestNS", region="us-east-1")
        resp = _MinimalResponse(provider="plan", error_type=None, is_fallback=False, usage=None)
        emitter._emit_sync(resp, 300, "m", Decimal("0"), True, 42, None)

    metrics = {m["MetricName"]: m for m in mock_cw.put_metric_data.call_args.kwargs["MetricData"]}
    assert "proxy.ttft" in metrics
    assert metrics["proxy.ttft"]["Value"] == 42


@patch("src.proxy.metrics.boto3")
@pytest.mark.asyncio
async def test_emit_skips_put_metric_data_when_disabled(mock_boto3: MagicMock) -> None:
    mock_cw = MagicMock()
    mock_boto3.client.return_value = mock_cw

    with patch("src.proxy.metrics.get_settings") as m:
        m.return_value.cloudwatch_metrics_enabled = False
        m.return_value.cloudwatch_namespace = "TestNS"
        m.return_value.bedrock_region = "us-east-1"

        emitter = CloudWatchMetricsEmitter(namespace="TestNS", region="us-east-1")
        resp = _MinimalResponse(provider="bedrock", error_type=None, is_fallback=False, usage=None)
        await emitter.emit(
            resp, 1, "m", cost=Decimal("0"), stream=False, ttft_ms=None, fallback_reason=None
        )

    mock_cw.put_metric_data.assert_not_called()


def test_normalize_model() -> None:
    assert _normalize_model("anthropic.claude-sonnet-4-5-20250514") != "unknown"
    assert _normalize_model("") == "unknown"
    assert _normalize_model("  ") == "unknown"


@pytest.mark.asyncio
async def test_otel_emit_noop_when_disabled() -> None:
    with patch("src.proxy.metrics.get_settings") as m:
        m.return_value.otel_metrics_enabled = False
        m.return_value.otel_user_metrics_enabled = False
        em = OTELMetricsEmitter()
    resp = _MinimalResponse(provider="plan", error_type=None, is_fallback=False, usage=None)
    await em.emit(resp, 10, "m", cost=Decimal("0"), stream=False, user_id="u1")
    # No OTLP export when disabled; emit returns without error


@pytest.mark.asyncio
async def test_composite_emitter_calls_both() -> None:
    cw = AsyncMock(spec=CloudWatchMetricsEmitter)
    otel = AsyncMock(spec=OTELMetricsEmitter)
    comp = CompositeMetricsEmitter(cw, otel)
    resp = _MinimalResponse(provider="bedrock", error_type=None, is_fallback=False, usage=None)
    await comp.emit(
        resp, 100, "x",
        cost=Decimal("0.001"), stream=True, ttft_ms=50,
        fallback_reason=None, user_id="user-42",
    )
    cw.emit.assert_awaited_once_with(
        resp, 100, "x",
        cost=Decimal("0.001"), stream=True, ttft_ms=50,
        fallback_reason=None, user_id="user-42",
    )
    otel.emit.assert_awaited_once_with(
        resp, 100, "x",
        cost=Decimal("0.001"), stream=True, ttft_ms=50,
        fallback_reason=None, user_id="user-42",
    )


def test_get_default_metrics_emitter_singleton() -> None:
    a = get_default_metrics_emitter()
    b = get_default_metrics_emitter()
    assert a is b
    assert isinstance(a, CompositeMetricsEmitter)
