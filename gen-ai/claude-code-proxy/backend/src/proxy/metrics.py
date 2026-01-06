"""CloudWatch metrics emitter."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

import boto3

from ..config import get_settings

# Shared executor for blocking boto3 calls
_executor = ThreadPoolExecutor(max_workers=2)


class ProxyResponseProtocol(Protocol):
    """Protocol for ProxyResponse to avoid circular import."""
    provider: str
    error_type: str | None
    is_fallback: bool
    usage: object | None


class CloudWatchMetricsEmitter:
    """Emits metrics to CloudWatch."""

    def __init__(self, namespace: str = "ClaudeCodeProxy", region: str | None = None):
        self._namespace = namespace
        self._region = region or get_settings().bedrock_region
        self._cw = boto3.client("cloudwatch", region_name=self._region)

    async def emit(self, response: ProxyResponseProtocol, latency_ms: int) -> None:
        """Emit metrics asynchronously (non-blocking)."""
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(_executor, self._emit_sync, response, latency_ms)
        except Exception:
            pass

    def _emit_sync(self, response: ProxyResponseProtocol, latency_ms: int) -> None:
        metrics = [
            {
                "MetricName": "RequestCount",
                "Value": 1,
                "Unit": "Count",
                "Dimensions": [{"Name": "Provider", "Value": response.provider}],
            },
            {
                "MetricName": "RequestLatency",
                "Value": latency_ms,
                "Unit": "Milliseconds",
                "Dimensions": [{"Name": "Provider", "Value": response.provider}],
            },
        ]

        if response.error_type:
            metrics.append({
                "MetricName": "ErrorCount",
                "Value": 1,
                "Unit": "Count",
                "Dimensions": [
                    {"Name": "ErrorType", "Value": response.error_type},
                    {"Name": "Provider", "Value": response.provider},
                ],
            })

        if response.is_fallback:
            metrics.append({
                "MetricName": "FallbackCount",
                "Value": 1,
                "Unit": "Count",
                "Dimensions": [],
            })

        if response.usage and response.provider == "bedrock":
            metrics.extend([
                {
                    "MetricName": "BedrockTokensUsed",
                    "Value": response.usage.input_tokens,
                    "Unit": "Count",
                    "Dimensions": [{"Name": "TokenType", "Value": "input"}],
                },
                {
                    "MetricName": "BedrockTokensUsed",
                    "Value": response.usage.output_tokens,
                    "Unit": "Count",
                    "Dimensions": [{"Name": "TokenType", "Value": "output"}],
                },
            ])

        self._cw.put_metric_data(Namespace=self._namespace, MetricData=metrics)
