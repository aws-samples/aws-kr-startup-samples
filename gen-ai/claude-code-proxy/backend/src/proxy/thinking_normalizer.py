"""Normalize Anthropic messages when thinking is enabled."""
from __future__ import annotations

import json
from typing import Any

try:
    from ..domain import AnthropicRequest
except ImportError:  # pragma: no cover
    from domain import AnthropicRequest


_THINKING_BLOCK_TYPES = {"thinking", "redacted_thinking"}


def ensure_thinking_prefix(request: AnthropicRequest) -> AnthropicRequest:
    """Ensure assistant messages start with thinking when thinking is enabled."""
    if not _thinking_enabled(request.thinking):
        return request

    for message in request.messages:
        if getattr(message, "role", None) != "assistant":
            continue
        if _content_starts_with_thinking(message.content):
            continue
        blocks = _normalize_content_blocks(message.content)
        message.content = _ensure_thinking_first(blocks)

    return request


def _thinking_enabled(thinking: dict[str, Any] | None) -> bool:
    if thinking is None:
        return False
    if isinstance(thinking, dict) and "type" in thinking:
        return thinking.get("type") == "enabled"
    return True


def _content_starts_with_thinking(content: Any) -> bool:
    if isinstance(content, list) and content:
        return _is_thinking_block(content[0])
    if isinstance(content, dict):
        return _is_thinking_block(content)
    return False


def _is_thinking_block(block: Any) -> bool:
    return isinstance(block, dict) and block.get("type") in _THINKING_BLOCK_TYPES


def _normalize_content_blocks(content: Any) -> list[dict[str, Any]]:
    if content is None:
        return []
    if isinstance(content, list):
        return [_normalize_block(block) for block in content]
    return [_normalize_block(content)]


def _normalize_block(block: Any) -> dict[str, Any]:
    if isinstance(block, dict):
        return block
    if isinstance(block, str):
        return {"type": "text", "text": block}
    return {"type": "text", "text": json.dumps(block)}


def _ensure_thinking_first(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not blocks:
        return [_redacted_thinking_block()]

    for index, block in enumerate(blocks):
        if _is_thinking_block(block):
            if index == 0:
                return blocks
            return [block] + blocks[:index] + blocks[index + 1 :]

    return [_redacted_thinking_block()] + blocks


def _redacted_thinking_block() -> dict[str, Any]:
    return {"type": "redacted_thinking", "data": ""}
