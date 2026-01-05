"""Decode Bedrock Converse stream events to Anthropic SSE format."""
import json
from dataclasses import dataclass
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
        yield {"type": "content_block_stop", "index": stop_event.get("contentBlockIndex", 0)}
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
            "output_tokens": usage.get("outputTokens", 0),
            "cache_read_input_tokens": usage.get("cacheReadInputTokens"),
            "cache_creation_input_tokens": usage.get("cacheCreationInputTokens"),
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
    return None


def _map_content_block_delta(delta: dict[str, Any]) -> dict[str, Any] | None:
    if "text" in delta:
        return {"type": "text_delta", "text": delta["text"]}
    if "toolUse" in delta:
        return {"type": "input_json_delta", "partial_json": delta["toolUse"].get("input", "")}
    return None


def _to_sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()
