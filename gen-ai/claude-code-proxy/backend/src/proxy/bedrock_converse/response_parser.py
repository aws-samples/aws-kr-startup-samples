"""Parse Bedrock Converse API responses to Anthropic format."""
import json
from typing import Any

try:
    from ...domain import AnthropicResponse, AnthropicUsage
except ImportError:  # pragma: no cover
    from domain import AnthropicResponse, AnthropicUsage


def parse_converse_response(
    data: dict[str, Any],
    model: str,
) -> tuple[AnthropicResponse, AnthropicUsage]:
    message = data.get("output", {}).get("message", {}) or {}
    content_blocks = _normalize_output_content(message.get("content", []))

    usage_data = data.get("usage", {}) or {}
    usage = AnthropicUsage(
        input_tokens=usage_data.get("inputTokens", 0),
        output_tokens=usage_data.get("outputTokens", 0),
        cache_read_input_tokens=usage_data.get("cacheReadInputTokens"),
        cache_creation_input_tokens=usage_data.get("cacheWriteInputTokens")
        if "cacheWriteInputTokens" in usage_data
        else usage_data.get("cacheCreationInputTokens"),
    )

    response = AnthropicResponse(
        id=data.get("id", f"msg_{hash(json.dumps(data, sort_keys=True))}"),
        content=content_blocks,
        model=model,
        stop_reason=_normalize_stop_reason(data.get("stopReason")),
        stop_sequence=None,
        usage=usage,
    )
    return response, usage


def _normalize_output_content(content: Any) -> list[dict[str, Any]]:
    if not isinstance(content, list):
        return []
    output: list[dict[str, Any]] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") in ("thinking", "redacted_thinking"):
            output.append(block)
        elif "text" in block:
            output.append({"type": "text", "text": block["text"]})
        elif "toolUse" in block:
            tool_use = block["toolUse"]
            output.append(
                {
                    "type": "tool_use",
                    "id": tool_use.get("toolUseId"),
                    "name": tool_use.get("name"),
                    "input": tool_use.get("input", {}),
                }
            )
        elif "toolResult" in block:
            tool_result = block["toolResult"]
            output.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_result.get("toolUseId"),
                    "content": _normalize_tool_result_output_content(tool_result.get("content")),
                    "is_error": tool_result.get("status") == "error",
                }
            )
        elif "reasoningContent" in block:
            thinking_block = _normalize_reasoning_content(block["reasoningContent"])
            if thinking_block:
                output.append(thinking_block)
    return output


def _normalize_tool_result_output_content(content: Any) -> list[dict[str, Any]]:
    if not isinstance(content, list):
        return []
    output: list[dict[str, Any]] = []
    for block in content:
        if isinstance(block, dict) and "text" in block:
            output.append({"type": "text", "text": block["text"]})
    return output


def _normalize_stop_reason(stop_reason: Any) -> str | None:
    if isinstance(stop_reason, str):
        return stop_reason
    return None


def _normalize_reasoning_content(content: Any) -> dict[str, Any] | None:
    if not isinstance(content, dict):
        return None

    if "redactedContent" in content:
        return {"type": "redacted_thinking", "data": content.get("redactedContent")}

    reasoning_text = None
    signature = None
    if "reasoningText" in content and isinstance(content["reasoningText"], dict):
        reasoning_text = content["reasoningText"].get("text")
        signature = content["reasoningText"].get("signature")
    else:
        reasoning_text = content.get("text")
        signature = content.get("signature")

    if reasoning_text is None and signature is None:
        return None

    thinking_block: dict[str, Any] = {
        "type": "thinking",
        "thinking": reasoning_text or "",
    }
    if signature is not None:
        thinking_block["signature"] = signature
    return thinking_block
