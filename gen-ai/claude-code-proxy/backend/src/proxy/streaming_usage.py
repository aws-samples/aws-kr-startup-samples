import json
from dataclasses import dataclass

from ..domain import AnthropicUsage


@dataclass
class StreamingUsageCollector:
    """Collect usage metadata from Anthropic-compatible SSE."""

    _buffer: str = ""
    _input_tokens: int = 0
    _usage: AnthropicUsage | None = None

    def feed(self, chunk: bytes) -> None:
        self._buffer += chunk.decode(errors="ignore")
        while "\n\n" in self._buffer:
            event, self._buffer = self._buffer.split("\n\n", 1)
            for line in event.splitlines():
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:") :].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                self._handle_event(data)

    def get_usage(self) -> AnthropicUsage | None:
        return self._usage

    def _handle_event(self, data: dict) -> None:
        if data.get("type") == "message_start":
            message = data.get("message") or {}
            usage = message.get("usage") or {}
            if "input_tokens" in usage:
                self._input_tokens = usage.get("input_tokens") or 0
            return

        if data.get("type") == "message_delta":
            usage = data.get("usage") or {}
            if "output_tokens" not in usage:
                return
            # Prefer input_tokens from message_delta if available (Bedrock provides it here)
            # Fall back to input_tokens from message_start
            input_tokens = usage.get("input_tokens") or self._input_tokens
            self._usage = AnthropicUsage(
                input_tokens=input_tokens,
                output_tokens=usage.get("output_tokens") or 0,
                cache_read_input_tokens=usage.get("cache_read_input_tokens"),
                cache_creation_input_tokens=usage.get("cache_creation_input_tokens"),
            )
