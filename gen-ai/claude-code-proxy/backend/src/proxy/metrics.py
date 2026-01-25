"""CloudWatch metrics emitter."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Protocol

import boto3

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
    ) -> None:
        """Emit metrics asynchronously (non-blocking)."""
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
            u = response.usage
            in_tok = getattr(u, "input_tokens", 0) or 0
            out_tok = getattr(u, "output_tokens", 0) or 0
            cache_read = getattr(u, "cache_read_input_tokens", None) or 0
            cache_write = getattr(u, "cache_creation_input_tokens", None) or 0
            token_dims_base = [
                {"Name": "Provider", "Value": response.provider},
                {"Name": "Model", "Value": model_norm},
            ]
            for val, ttype in [
                (in_tok, "input"),
                (out_tok, "output"),
                (cache_read, "cache_read"),
                (cache_write, "cache_write"),
            ]:
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
