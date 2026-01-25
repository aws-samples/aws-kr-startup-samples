"""CloudWatch and OTEL metrics emitters."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Protocol

import boto3
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from ..config import get_settings
from ..domain import Provider
from ..domain.pricing import PricingConfig

# Shared executor for blocking boto3 calls
_executor = ThreadPoolExecutor(max_workers=2)


class ProxyResponseProtocol(Protocol):
    """Protocol for ProxyResponse to avoid circular import."""

    provider: Provider
    error_type: str | None
    is_fallback: bool
    usage: object | None


class MetricsEmitterProtocol(Protocol):
    """Protocol for metrics emitters (CloudWatch, OTEL, Composite)."""

    async def emit(
        self,
        response: "ProxyResponseProtocol",
        latency_ms: int,
        model: str,
        *,
        cost: Decimal = ...,
        stream: bool = ...,
        ttft_ms: int | None = ...,
        fallback_reason: str | None = ...,
        user_id: str | None = ...,
    ) -> None: ...


def _normalize_model(model: str) -> str:
    if not model or not model.strip():
        return "unknown"
    try:
        return PricingConfig.normalize_model_id(model)
    except Exception:
        return "unknown"


class CloudWatchMetricsEmitter:
    """Emits metrics to CloudWatch."""

    def __init__(self, namespace: str | None = None, region: str | None = None):
        self._namespace = namespace or get_settings().cloudwatch_namespace
        self._region = region or get_settings().bedrock_region
        self._cw = boto3.client("cloudwatch", region_name=self._region)

    async def emit(
        self,
        response: ProxyResponseProtocol,
        latency_ms: int,
        model: str,
        *,
        cost: Decimal = Decimal("0"),
        stream: bool = False,
        ttft_ms: int | None = None,
        fallback_reason: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Emit metrics asynchronously (non-blocking). user_id ignored (CloudWatch)."""
        if not get_settings().cloudwatch_metrics_enabled:
            return
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                _executor,
                self._emit_sync,
                response,
                latency_ms,
                model,
                cost,
                stream,
                ttft_ms,
                fallback_reason,
            )
        except Exception:
            pass

    def _emit_sync(
        self,
        response: ProxyResponseProtocol,
        latency_ms: int,
        model: str,
        cost: Decimal,
        stream: bool,
        ttft_ms: int | None,
        fallback_reason: str | None,
    ) -> None:
        model_norm = _normalize_model(model)
        status = "success" if not response.error_type else "error"
        stream_str = "true" if stream else "false"
        base_dims = [
            {"Name": "Provider", "Value": response.provider},
            {"Name": "Model", "Value": model_norm},
            {"Name": "Status", "Value": status},
            {"Name": "Stream", "Value": stream_str},
        ]

        metrics = [
            {"MetricName": "proxy.requests", "Value": 1, "Unit": "Count", "Dimensions": base_dims},
            {
                "MetricName": "proxy.latency",
                "Value": latency_ms,
                "Unit": "Milliseconds",
                "Dimensions": base_dims,
            },
        ]

        if ttft_ms is not None:
            metrics.append(
                {
                    "MetricName": "proxy.ttft",
                    "Value": ttft_ms,
                    "Unit": "Milliseconds",
                    "Dimensions": [
                        {"Name": "Provider", "Value": response.provider},
                        {"Name": "Model", "Value": model_norm},
                    ],
                }
            )

        if response.usage:
            token_dims_base = [
                {"Name": "Provider", "Value": response.provider},
                {"Name": "Model", "Value": model_norm},
            ]
            for val, ttype in _iter_token_counts(response.usage):
                if val > 0:
                    metrics.append(
                        {
                            "MetricName": "proxy.tokens",
                            "Value": val,
                            "Unit": "Count",
                            "Dimensions": token_dims_base + [{"Name": "TokenType", "Value": ttype}],
                        }
                    )

        cost_dims = [
            {"Name": "Provider", "Value": response.provider},
            {"Name": "Model", "Value": model_norm},
        ]
        metrics.append(
            {
                "MetricName": "proxy.cost",
                "Value": float(cost),
                "Dimensions": cost_dims,
            }
        )

        if response.error_type:
            metrics.append(
                {
                    "MetricName": "proxy.errors",
                    "Value": 1,
                    "Unit": "Count",
                    "Dimensions": [
                        {"Name": "Provider", "Value": response.provider},
                        {"Name": "ErrorType", "Value": response.error_type},
                    ],
                }
            )

        if response.is_fallback and fallback_reason:
            metrics.append(
                {
                    "MetricName": "proxy.fallbacks",
                    "Value": 1,
                    "Unit": "Count",
                    "Dimensions": [
                        {"Name": "FromProvider", "Value": "plan"},
                        {"Name": "ToProvider", "Value": response.provider},
                        {"Name": "Reason", "Value": fallback_reason},
                    ],
                }
            )

        self._cw.put_metric_data(Namespace=self._namespace, MetricData=metrics)


def _grpc_endpoint_from_url(url: str) -> str:
    """Strip http(s) scheme for gRPC endpoint (host:port)."""
    s = url.strip()
    for prefix in ("https://", "http://"):
        if s.lower().startswith(prefix):
            return s[len(prefix) :]
    return s


def _iter_token_counts(usage: object | None) -> list[tuple[int, str]]:
    """(value, token_type) for input, output, cache_read, cache_write. DRY for CW and OTEL."""
    if not usage:
        return []
    return [
        (getattr(usage, "input_tokens", 0) or 0, "input"),
        (getattr(usage, "output_tokens", 0) or 0, "output"),
        (getattr(usage, "cache_read_input_tokens", None) or 0, "cache_read"),
        (getattr(usage, "cache_creation_input_tokens", None) or 0, "cache_write"),
    ]


OTEL_METER_VERSION = "0.1.0"


class OTELMetricsEmitter:
    """Emits Tier 1 (proxy.*) and Tier 2 (proxy.user.*) metrics via OTLP gRPC."""

    def __init__(self) -> None:
        s = get_settings()
        self._enabled = s.otel_metrics_enabled
        self._user_enabled = s.otel_user_metrics_enabled
        self._meter_provider: MeterProvider | None = None
        self._meter = None  # Set when _enabled; OTEL Meter for create_counter/create_histogram
        self._user_requests = None
        self._user_tokens = None
        self._user_cost = None
        self._requests = None
        self._latency = None
        self._ttft = None
        self._tokens = None
        self._cost = None
        self._errors = None
        self._fallbacks = None

        if not self._enabled:
            return

        endpoint = _grpc_endpoint_from_url(s.otel_endpoint)
        exporter = OTLPMetricExporter(endpoint=endpoint or None, insecure=s.otel_insecure)
        reader = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=s.otel_export_interval_ms,
            export_timeout_millis=s.otel_export_timeout_ms,
        )
        resource = Resource.create(attributes={SERVICE_NAME: s.otel_service_name})
        self._meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        meter = self._meter_provider.get_meter(s.otel_service_name, OTEL_METER_VERSION)
        self._meter = meter

        self._requests = meter.create_counter(
            "proxy.requests", unit="1", description="Request count"
        )
        self._latency = meter.create_histogram(
            "proxy.latency", unit="ms", description="Request latency"
        )
        self._ttft = meter.create_histogram(
            "proxy.ttft", unit="ms", description="Time to first token (streaming)"
        )
        self._tokens = meter.create_counter("proxy.tokens", unit="token", description="Token usage")
        self._cost = meter.create_counter("proxy.cost", unit="usd", description="Estimated cost")
        self._errors = meter.create_counter("proxy.errors", unit="1", description="Error count")
        self._fallbacks = meter.create_counter(
            "proxy.fallbacks", unit="1", description="Fallback count"
        )

        if self._user_enabled:
            self._user_requests = meter.create_counter(
                "proxy.user.requests", unit="1", description="Per-user request count"
            )
            self._user_tokens = meter.create_counter(
                "proxy.user.tokens", unit="token", description="Per-user token usage"
            )
            self._user_cost = meter.create_counter(
                "proxy.user.cost", unit="usd", description="Per-user estimated cost"
            )

    async def emit(
        self,
        response: ProxyResponseProtocol,
        latency_ms: int,
        model: str,
        *,
        cost: Decimal = Decimal("0"),
        stream: bool = False,
        ttft_ms: int | None = None,
        fallback_reason: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Record metrics. Export is handled by PeriodicExportingMetricReader."""
        if not self._enabled or self._meter is None:
            return
        # Narrow types after early return (enabled path always has instruments)
        assert self._requests is not None
        assert self._latency is not None
        assert self._tokens is not None
        assert self._cost is not None
        assert self._errors is not None
        assert self._fallbacks is not None
        assert self._ttft is not None

        model_norm = _normalize_model(model)
        status = "success" if not response.error_type else "error"
        attrs = {
            "provider": response.provider,
            "model": model_norm,
            "status": status,
            "stream": "true" if stream else "false",
        }

        self._requests.add(1, attrs)
        self._latency.record(latency_ms, attrs)

        if ttft_ms is not None:
            self._ttft.record(ttft_ms, {"provider": response.provider, "model": model_norm})

        if response.usage:
            base = {"provider": response.provider, "model": model_norm}
            for val, ttype in _iter_token_counts(response.usage):
                if val > 0:
                    self._tokens.add(val, {**base, "token_type": ttype})

        self._cost.add(float(cost), {"provider": response.provider, "model": model_norm})

        if response.error_type:
            self._errors.add(
                1, {"provider": response.provider, "error_type": response.error_type}
            )

        if response.is_fallback and fallback_reason:
            self._fallbacks.add(
                1,
                {
                    "from_provider": "plan",
                    "to_provider": response.provider,
                    "reason": fallback_reason,
                },
            )

        # Tier 2: per-user (OTEL only)
        if (
            self._user_enabled
            and user_id
            and self._user_requests is not None
            and self._user_cost is not None
        ):
            ua = {
                "user_id": user_id,
                "provider": response.provider,
                "model": model_norm,
                "status": status,
            }
            self._user_requests.add(1, ua)
            self._user_cost.add(
                float(cost),
                {"user_id": user_id, "provider": response.provider, "model": model_norm},
            )
            if response.usage and self._user_tokens is not None:
                base_u = {"user_id": user_id, "provider": response.provider, "model": model_norm}
                for val, ttype in _iter_token_counts(response.usage):
                    if val > 0:
                        self._user_tokens.add(val, {**base_u, "token_type": ttype})


class CompositeMetricsEmitter:
    """Forwards emit() to CloudWatch and OTEL. Each child handles its own enabled check."""

    def __init__(
        self,
        cloudwatch: CloudWatchMetricsEmitter,
        otel: OTELMetricsEmitter,
    ) -> None:
        self._cw = cloudwatch
        self._otel = otel

    async def emit(
        self,
        response: ProxyResponseProtocol,
        latency_ms: int,
        model: str,
        *,
        cost: Decimal = Decimal("0"),
        stream: bool = False,
        ttft_ms: int | None = None,
        fallback_reason: str | None = None,
        user_id: str | None = None,
    ) -> None:
        await self._cw.emit(
            response, latency_ms, model,
            cost=cost, stream=stream, ttft_ms=ttft_ms,
            fallback_reason=fallback_reason, user_id=user_id,
        )
        await self._otel.emit(
            response, latency_ms, model,
            cost=cost, stream=stream, ttft_ms=ttft_ms,
            fallback_reason=fallback_reason, user_id=user_id,
        )


_default_emitter: CompositeMetricsEmitter | None = None


def get_default_metrics_emitter() -> CompositeMetricsEmitter:
    """Singleton Composite (CloudWatch + OTEL). OTEL on/off via PROXY_OTEL_METRICS_ENABLED."""
    global _default_emitter
    if _default_emitter is None:
        _default_emitter = CompositeMetricsEmitter(
            CloudWatchMetricsEmitter(),
            OTELMetricsEmitter(),
        )
    return _default_emitter
