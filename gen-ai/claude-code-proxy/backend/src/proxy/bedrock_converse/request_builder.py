"""Build Bedrock Converse API requests from Anthropic format."""

import json
from typing import Any

try:
    from ...domain import AnthropicRequest, CachingStrategy
except ImportError:  # pragma: no cover
    from domain import AnthropicRequest, CachingStrategy


MAX_CACHE_POINTS = 4
ONE_HOUR_TTL_SUPPORTED_MODEL_MARKERS = (
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    "claude-opus-4-6",
)


def _has_cache_control(block: Any) -> bool:
    """Check if a block has cache_control with type 'ephemeral'."""
    if not isinstance(block, dict):
        return False
    cache_control = block.get("cache_control")
    if not isinstance(cache_control, dict):
        return False
    return cache_control.get("type") == "ephemeral"


def _resolve_cache_ttl(
    caching_strategy: CachingStrategy | str,
    model_id: str | None,
) -> str | None:
    if caching_strategy == CachingStrategy.OFF:
        return None
    if caching_strategy == CachingStrategy.ONE_HOUR:
        if model_id and any(marker in model_id for marker in ONE_HOUR_TTL_SUPPORTED_MODEL_MARKERS):
            return CachingStrategy.ONE_HOUR.value
    return CachingStrategy.FIVE_MINUTES.value


def _build_cache_point_block(ttl: str) -> dict[str, Any]:
    return {"cachePoint": {"type": "default", "ttl": ttl}}


def _append_cache_point(
    result: list[dict[str, Any]],
    counter: dict[str, int],
    *,
    ttl: str | None,
) -> None:
    if ttl is None:
        return
    if counter["count"] >= MAX_CACHE_POINTS:
        return
    result.append(_build_cache_point_block(ttl))
    counter["count"] += 1


def build_converse_request(
    request: AnthropicRequest,
    *,
    caching_strategy: CachingStrategy | str = CachingStrategy.FIVE_MINUTES,
    model_id: str | None = None,
) -> dict[str, Any]:
    cache_counter = {"count": 0}
    cache_ttl = _resolve_cache_ttl(caching_strategy, model_id or request.model)
    messages = [_normalize_message(msg, cache_counter, cache_ttl) for msg in request.messages]
    payload: dict[str, Any] = {"messages": messages}

    system_blocks = _normalize_system(request.system, cache_counter, cache_ttl)
    if system_blocks:
        payload["system"] = system_blocks

    inference_config = _build_inference_config(request)
    if inference_config:
        payload["inferenceConfig"] = inference_config

    tool_config = _build_tool_config(request.tools, request.tool_choice, cache_counter, cache_ttl)
    if tool_config:
        payload["toolConfig"] = tool_config

    # Bedrock requestMetadata is intentionally disabled.
    # Claude Code metadata is not used by the proxy runtime.

    additional_fields = _build_additional_model_request_fields(request)
    if additional_fields:
        payload["additionalModelRequestFields"] = additional_fields

    return payload


def _normalize_message(
    message: Any,
    cache_counter: dict[str, int],
    cache_ttl: str | None,
) -> dict[str, Any]:
    content = _normalize_content(message.content, cache_counter, cache_ttl)
    return {"role": message.role, "content": content}


def _normalize_content(
    content: Any,
    cache_counter: dict[str, int],
    cache_ttl: str | None,
) -> list[dict[str, Any]]:
    if content is None:
        return []
    if isinstance(content, str):
        return [{"text": content}]
    if isinstance(content, dict):
        result = [_normalize_content_block(content)]
        if _has_cache_control(content):
            _append_cache_point(result, cache_counter, ttl=cache_ttl)
        return result
    if isinstance(content, list):
        result: list[dict[str, Any]] = []
        for item in content:
            result.append(_normalize_content_block(item))
            if _has_cache_control(item):
                _append_cache_point(result, cache_counter, ttl=cache_ttl)
        return result
    return [{"text": json.dumps(content)}]


def _normalize_system(
    system: Any,
    cache_counter: dict[str, int],
    cache_ttl: str | None,
) -> list[dict[str, Any]]:
    if system is None:
        return []
    if isinstance(system, str):
        return [{"text": system}]
    if isinstance(system, dict):
        result = [_normalize_system_block(system)]
        if _has_cache_control(system):
            _append_cache_point(result, cache_counter, ttl=cache_ttl)
        return result
    if isinstance(system, list):
        result: list[dict[str, Any]] = []
        for item in system:
            result.append(_normalize_system_block(item))
            if _has_cache_control(item):
                _append_cache_point(result, cache_counter, ttl=cache_ttl)
        return result
    return [{"text": json.dumps(system)}]


def _normalize_system_block(block: Any) -> dict[str, Any]:
    if isinstance(block, str):
        return {"text": block}
    if isinstance(block, dict):
        if block.get("type") == "text" and "text" in block:
            return {"text": block["text"]}
        if "text" in block:
            return {"text": block["text"]}
    return {"text": json.dumps(block)}


def _normalize_content_block(block: Any) -> dict[str, Any]:
    if isinstance(block, str):
        return {"text": block}
    if not isinstance(block, dict):
        return {"text": json.dumps(block)}

    block_type = block.get("type")
    if block_type == "text":
        return {"text": block.get("text", "")}
    if block_type == "tool_use":
        return {
            "toolUse": {
                "toolUseId": block.get("id"),
                "name": block.get("name"),
                "input": block.get("input", {}),
            }
        }
    if block_type == "tool_result":
        tool_use_id = block.get("tool_use_id") or block.get("toolUseId")
        return {
            "toolResult": {
                "toolUseId": tool_use_id,
                "content": _normalize_tool_result_content(block.get("content")),
                "status": "error" if block.get("is_error") else "success",
            }
        }
    if block_type == "thinking":
        return {"reasoningContent": _normalize_thinking_block(block)}
    if block_type == "redacted_thinking":
        return {"reasoningContent": {"redactedContent": block.get("data", "")}}

    if "reasoningContent" in block:
        return {"reasoningContent": block["reasoningContent"]}
    if "text" in block:
        return {"text": block["text"]}
    if "toolUse" in block or "toolResult" in block:
        return block

    return {"text": json.dumps(block)}


def _normalize_thinking_block(block: dict[str, Any]) -> dict[str, Any]:
    reasoning_text = block.get("thinking") or block.get("text") or ""
    reasoning_payload: dict[str, Any] = {"text": reasoning_text}
    if (signature := block.get("signature")) is not None:
        reasoning_payload["signature"] = signature
    return {"reasoningText": reasoning_payload}


def _normalize_tool_result_content(content: Any) -> list[dict[str, Any]]:
    if content is None:
        return []
    if isinstance(content, str):
        return [{"text": content}]
    if isinstance(content, dict):
        return [_normalize_content_block(content)]
    if isinstance(content, list):
        return [_normalize_content_block(item) for item in content]
    return [{"text": json.dumps(content)}]


def _build_inference_config(request: AnthropicRequest) -> dict[str, Any]:
    inference: dict[str, Any] = {}
    if request.max_tokens is not None:
        inference["maxTokens"] = request.max_tokens
    if request.temperature is not None:
        inference["temperature"] = request.temperature
    if request.top_p is not None:
        inference["topP"] = request.top_p
    if request.top_k is not None:
        inference["topK"] = request.top_k
    if request.stop_sequences:
        inference["stopSequences"] = request.stop_sequences
    return inference


def _build_tool_config(
    tools: list[dict[str, Any]] | None,
    tool_choice: dict[str, Any] | str | None,
    cache_counter: dict[str, int],
    cache_ttl: str | None,
) -> dict[str, Any] | None:
    if not tools:
        return None
    tool_blocks: list[dict[str, Any]] = []
    for tool in tools:
        tool_blocks.append(_normalize_tool(tool))
        if _has_cache_control(tool):
            _append_cache_point(tool_blocks, cache_counter, ttl=cache_ttl)
    tool_config: dict[str, Any] = {"tools": tool_blocks}
    choice_block = _normalize_tool_choice(tool_choice)
    if choice_block:
        tool_config["toolChoice"] = choice_block
    return tool_config


def _normalize_tool(tool: dict[str, Any]) -> dict[str, Any]:
    if "toolSpec" in tool:
        return {"toolSpec": tool["toolSpec"]}
    if tool.get("type") == "function" and "function" in tool:
        func = tool.get("function", {})
        return {
            "toolSpec": {
                "name": func.get("name") or tool.get("name"),
                "description": func.get("description"),
                "inputSchema": {"json": func.get("parameters", {})},
            }
        }
    return {
        "toolSpec": {
            "name": tool.get("name"),
            "description": tool.get("description"),
            "inputSchema": {"json": tool.get("input_schema", {})},
        }
    }


def _normalize_tool_choice(choice: dict[str, Any] | str | None) -> dict[str, Any] | None:
    if choice is None:
        return None
    if isinstance(choice, str):
        if choice == "auto":
            return {"auto": {}}
        if choice in ("any", "required"):
            return {"any": {}}
        return None
    choice_type = choice.get("type")
    if choice_type == "auto":
        return {"auto": {}}
    if choice_type in ("any", "required"):
        return {"any": {}}
    if choice_type == "tool":
        name = choice.get("name")
        if name:
            return {"tool": {"name": name}}
    tool_choice = choice.get("tool") or choice.get("function")
    if isinstance(tool_choice, dict) and tool_choice.get("name"):
        return {"tool": {"name": tool_choice["name"]}}
    return None


def _build_additional_model_request_fields(
    request: AnthropicRequest,
) -> dict[str, Any] | None:
    fields: dict[str, Any] = {}
    if request.thinking is not None:
        fields["thinking"] = request.thinking
    return fields or None
