"""Normalize Anthropic messages when thinking is enabled.

LiteLLM 방식을 따름:
1. 가짜 redacted_thinking 블록 생성하지 않음
2. invalid redacted_thinking 블록 제거 (빈 data 또는 비문자열 data)
3. 기존 thinking/redacted_thinking 블록은 앞으로만 이동
4. assistant 메시지에 tool_use가 있는데 thinking_blocks가 없으면 thinking param 드롭
"""
from __future__ import annotations

from typing import Any

try:
    from ..domain import AnthropicRequest
except ImportError:  # pragma: no cover
    from domain import AnthropicRequest


_THINKING_BLOCK_TYPES = {"thinking", "redacted_thinking"}


def ensure_thinking_prefix(request: AnthropicRequest) -> AnthropicRequest:
    """Ensure assistant messages start with thinking when thinking is enabled.

    LiteLLM 방식: 가짜 redacted_thinking을 삽입하지 않고, 기존 thinking 블록만 앞으로 이동.
    """
    if not _thinking_enabled(request.thinking):
        return request

    for message in request.messages:
        if getattr(message, "role", None) != "assistant":
            continue

        # 리스트가 아닌 content는 건드리지 않음 (가짜 블록 생성하지 않음)
        if not isinstance(message.content, list):
            continue

        # 이미 thinking으로 시작하면 OK
        if _content_starts_with_thinking(message.content):
            continue

        # 기존 thinking 블록이 있으면 앞으로만 이동
        message.content = _move_thinking_to_first(message.content)

    return request


def remove_invalid_redacted_thinking(request: AnthropicRequest) -> AnthropicRequest:
    """Remove invalid redacted_thinking blocks from assistant messages.

    Invalid: 빈 문자열 data, 비문자열 data, data 키 없음
    """
    for message in request.messages:
        if getattr(message, "role", None) != "assistant":
            continue

        if not isinstance(message.content, list):
            continue

        message.content = [
            block
            for block in message.content
            if not _is_invalid_redacted_thinking(block)
        ]

    return request


def should_drop_thinking_param(request: AnthropicRequest) -> bool:
    """Check if thinking param should be dropped.

    LiteLLM 방식: assistant 메시지에 tool_use가 있는데 thinking 블록이 없으면 True.
    이 경우 API에서 "Expected thinking or redacted_thinking, but found tool_use" 에러 발생.
    """
    if not _thinking_enabled(request.thinking):
        return False

    # 마지막 tool_use가 있는 assistant 메시지 찾기
    last_assistant_with_tool_use = None
    for message in request.messages:
        if getattr(message, "role", None) != "assistant":
            continue
        if _has_tool_use(message.content):
            last_assistant_with_tool_use = message

    if last_assistant_with_tool_use is None:
        return False

    # thinking 블록이 있는지 확인
    return not _has_thinking_block(last_assistant_with_tool_use.content)


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


def _is_invalid_redacted_thinking(block: Any) -> bool:
    """Check if block is an invalid redacted_thinking.

    Invalid: 빈 문자열 data, 비문자열 data, data 키 없음
    """
    if not isinstance(block, dict):
        return False
    if block.get("type") != "redacted_thinking":
        return False

    data = block.get("data")
    # data가 없거나, 문자열이 아니거나, 빈 문자열이면 invalid
    if data is None:
        return True
    if not isinstance(data, str):
        return True
    if data == "":
        return True

    return False


def _move_thinking_to_first(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Move existing thinking block to first position if found.

    LiteLLM 방식: 가짜 thinking 블록 생성하지 않음.
    """
    if not blocks:
        return blocks

    for index, block in enumerate(blocks):
        if _is_thinking_block(block):
            if index == 0:
                return blocks
            # 앞으로 이동
            return [block] + blocks[:index] + blocks[index + 1 :]

    # thinking 블록이 없으면 그대로 반환 (가짜 생성하지 않음)
    return blocks


def _has_tool_use(content: Any) -> bool:
    """Check if content has tool_use block."""
    if not isinstance(content, list):
        return False

    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            return True

    return False


def _has_thinking_block(content: Any) -> bool:
    """Check if content has thinking or redacted_thinking block."""
    if not isinstance(content, list):
        return False

    for block in content:
        if _is_thinking_block(block):
            return True

    return False
