"""Decode Bedrock Converse stream events to Anthropic SSE format."""
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from botocore.eventstream import EventStreamBuffer
from botocore.loaders import Loader
from botocore.model import ServiceModel
from botocore.parsers import EventStreamJSONParser

_response_stream_shape_cache = None


def _get_response_stream_shape():
    global _response_stream_shape_cache
    if _response_stream_shape_cache is None:
        loader = Loader()
        service_dict = loader.load_service_model("bedrock-runtime", "service-2")
        service_model = ServiceModel(service_dict)
        _response_stream_shape_cache = service_model.shape_for("ResponseStream")
    return _response_stream_shape_cache


@dataclass
class StreamState:
    message_id: str
    stop_reason: str | None = None
    usage: dict[str, Any] | None = None
    message_started: bool = False
    message_stopped: bool = False
    started_blocks: set[int] = field(default_factory=set)


class ConverseStreamDecoder:
    def __init__(self) -> None:
        self._parser = EventStreamJSONParser()
        self._buffer = EventStreamBuffer()

    def feed(self, chunk: bytes) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        self._buffer.add_data(chunk)
        for event in self._buffer:
            response_dict = event.to_response_dict()
            parsed = self._parser.parse(response_dict, _get_response_stream_shape())
            if response_dict["status_code"] != 200:
                raise ValueError(response_dict.get("body", b"").decode(errors="ignore"))
            payload = None
            if "chunk" in parsed and parsed["chunk"]:
                payload = parsed["chunk"].get("bytes")
            elif response_dict.get("body"):
                payload = response_dict["body"]
            if not payload:
                continue
            events.append(json.loads(payload.decode()))
        return events


async def iter_anthropic_sse(
    response_stream: AsyncIterator[bytes],
    model: str,
    message_id: str,
) -> AsyncIterator[bytes]:
    decoder = ConverseStreamDecoder()
    state = StreamState(message_id=message_id)

    async for chunk in response_stream:
        for event in decoder.feed(chunk):
            async for payload in _convert_converse_event(event, state, model):
                yield _to_sse(payload)

    async for payload in _flush_message_delta(state):
        yield _to_sse(payload)
    if state.message_started and not state.message_stopped:
        yield _to_sse({"type": "message_stop"})


async def _convert_converse_event(
    event: dict[str, Any],
    state: StreamState,
    model: str,
) -> AsyncIterator[dict[str, Any]]:
    if "messageStart" in event and not state.message_started:
        state.message_started = True
        yield {
            "type": "message_start",
            "message": {
                "id": state.message_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": model,
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        }
        return

    if "contentBlockStart" in event:
        start_event = event["contentBlockStart"]
        index = start_event.get("contentBlockIndex", 0)
        start = start_event.get("start", {})
        content_block = _map_content_block_start(start)
        if content_block:
            state.started_blocks.add(index)
            yield {
                "type": "content_block_start",
                "index": index,
                "content_block": content_block,
            }
        return

    if "contentBlockDelta" in event:
        delta_event = event["contentBlockDelta"]
        index = delta_event.get("contentBlockIndex", 0)
        delta = delta_event.get("delta", {})
        if "reasoningContent" in delta and index not in state.started_blocks:
            content_block = _map_reasoning_content_start(delta["reasoningContent"])
            if content_block:
                state.started_blocks.add(index)
                yield {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": content_block,
                }
        delta_payload = _map_content_block_delta(delta)
        if delta_payload:
            yield {
                "type": "content_block_delta",
                "index": index,
                "delta": delta_payload,
            }
        return

    if "contentBlockStop" in event:
        stop_event = event["contentBlockStop"]
        index = stop_event.get("contentBlockIndex", 0)
        state.started_blocks.discard(index)
        yield {"type": "content_block_stop", "index": index}
        return

    if "messageStop" in event:
        stop_reason = event["messageStop"].get("stopReason")
        state.stop_reason = stop_reason if isinstance(stop_reason, str) else None
        if state.usage is not None:
            async for payload in _flush_message_delta(state):
                yield payload
            yield {"type": "message_stop"}
            state.message_stopped = True
        return

    if "metadata" in event:
        metadata = event["metadata"]
        usage = metadata.get("usage", {})
        state.usage = usage
        if state.stop_reason is not None:
            async for payload in _flush_message_delta(state):
                yield payload
            yield {"type": "message_stop"}
            state.message_stopped = True
        return


async def _flush_message_delta(state: StreamState) -> AsyncIterator[dict[str, Any]]:
    if state.stop_reason is None and not state.usage:
        return
    usage = state.usage or {}
    yield {
        "type": "message_delta",
        "delta": {"stop_reason": state.stop_reason, "stop_sequence": None},
        "usage": {
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
            "cache_read_input_tokens": usage.get("cacheReadInputTokens"),
            "cache_creation_input_tokens": usage.get("cacheWriteInputTokens")
            if "cacheWriteInputTokens" in usage
            else usage.get("cacheCreationInputTokens"),
        },
    }
    state.stop_reason = None
    state.usage = None


def _map_content_block_start(start: dict[str, Any]) -> dict[str, Any] | None:
    if "text" in start:
        return {"type": "text", "text": ""}
    if "toolUse" in start:
        tool = start["toolUse"]
        return {
            "type": "tool_use",
            "id": tool.get("toolUseId"),
            "name": tool.get("name"),
            "input": {},
        }
    if "reasoningContent" in start:
        return _map_reasoning_content_start(start["reasoningContent"])
    return None


def _map_content_block_delta(delta: dict[str, Any]) -> dict[str, Any] | None:
    if "text" in delta:
        return {"type": "text_delta", "text": delta["text"]}
    if "toolUse" in delta:
        return {"type": "input_json_delta", "partial_json": delta["toolUse"].get("input", "")}
    if "reasoningContent" in delta:
        return _map_reasoning_content_delta(delta["reasoningContent"])
    return None


def _map_reasoning_content_start(content: Any) -> dict[str, Any] | None:
    if not isinstance(content, dict):
        return None
    if "redactedContent" in content:
        return {"type": "redacted_thinking", "data": content.get("redactedContent")}

    thinking_block: dict[str, Any] = {"type": "thinking", "thinking": ""}
    if "signature" in content and "text" not in content:
        thinking_block["signature"] = content.get("signature") or ""
    return thinking_block


def _map_reasoning_content_delta(content: Any) -> dict[str, Any] | None:
    if not isinstance(content, dict):
        return None
    if "text" in content:
        return {"type": "thinking_delta", "thinking": content["text"]}
    if "signature" in content:
        return {"type": "signature_delta", "signature": content["signature"]}
    return None


def _to_sse(payload: dict[str, Any]) -> bytes:
    event_type = payload.get("type") or "message"
    return f"event: {event_type}\n" f"data: {json.dumps(payload)}\n\n".encode()
