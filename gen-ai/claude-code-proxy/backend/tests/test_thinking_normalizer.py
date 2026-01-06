"""Tests for thinking_normalizer module.

LiteLLM 방식을 따름:
1. 가짜 redacted_thinking 블록 생성하지 않음
2. invalid redacted_thinking 블록 제거 (빈 data 또는 비문자열 data)
3. 기존 thinking/redacted_thinking 블록은 앞으로만 이동
4. assistant 메시지에 tool_calls가 있는데 thinking_blocks가 없으면 thinking param 드롭
"""
from domain import AnthropicRequest
from thinking_normalizer import (
    ensure_thinking_prefix,
    remove_invalid_redacted_thinking,
    should_drop_thinking_param,
)


# =============================================================================
# ensure_thinking_prefix 테스트
# =============================================================================


class TestEnsureThinkingPrefix:
    """ensure_thinking_prefix 함수 테스트."""

    def test_does_not_insert_fake_redacted_thinking(self) -> None:
        """가짜 redacted_thinking 블록을 삽입하지 않아야 함."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "World"},
            ],
            thinking={"type": "enabled", "budget_tokens": 128},
        )

        ensure_thinking_prefix(request)

        # LiteLLM 방식: 가짜 redacted_thinking 삽입하지 않음
        assistant_content = request.messages[1].content
        # 문자열 content는 그대로 유지
        assert assistant_content == "World"

    def test_does_not_insert_fake_redacted_thinking_for_list_content(self) -> None:
        """리스트 content에도 가짜 redacted_thinking 블록을 삽입하지 않아야 함."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "World"}],
                },
            ],
            thinking={"type": "enabled", "budget_tokens": 128},
        )

        ensure_thinking_prefix(request)

        # 가짜 redacted_thinking 없이 원본 유지
        assistant_content = request.messages[1].content
        assert len(assistant_content) == 1
        assert assistant_content[0] == {"type": "text", "text": "World"}

    def test_moves_existing_thinking_to_first(self) -> None:
        """기존 thinking 블록이 있으면 맨 앞으로 이동."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Answer"},
                        {"type": "thinking", "thinking": "Thought", "signature": "sig"},
                    ],
                }
            ],
            thinking={"type": "enabled", "budget_tokens": 256},
        )

        ensure_thinking_prefix(request)

        assistant_content = request.messages[0].content
        assert assistant_content[0]["type"] == "thinking"
        assert assistant_content[0]["signature"] == "sig"
        assert assistant_content[1] == {"type": "text", "text": "Answer"}

    def test_moves_existing_redacted_thinking_to_first(self) -> None:
        """기존 redacted_thinking 블록이 있으면 맨 앞으로 이동."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Answer"},
                        {"type": "redacted_thinking", "data": "encrypted_data_here"},
                    ],
                }
            ],
            thinking={"type": "enabled", "budget_tokens": 256},
        )

        ensure_thinking_prefix(request)

        assistant_content = request.messages[0].content
        assert assistant_content[0]["type"] == "redacted_thinking"
        assert assistant_content[0]["data"] == "encrypted_data_here"
        assert assistant_content[1] == {"type": "text", "text": "Answer"}

    def test_keeps_thinking_at_first_position(self) -> None:
        """thinking이 이미 첫 번째면 그대로 유지."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "Thought", "signature": "sig"},
                        {"type": "text", "text": "Answer"},
                    ],
                }
            ],
            thinking={"type": "enabled", "budget_tokens": 256},
        )

        ensure_thinking_prefix(request)

        assistant_content = request.messages[0].content
        assert assistant_content[0]["type"] == "thinking"
        assert assistant_content[1] == {"type": "text", "text": "Answer"}

    def test_does_nothing_when_thinking_disabled(self) -> None:
        """thinking이 비활성화면 아무것도 안 함."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "assistant", "content": "World"},
            ],
            thinking=None,
        )

        ensure_thinking_prefix(request)

        assert request.messages[0].content == "World"

    def test_does_nothing_for_user_messages(self) -> None:
        """user 메시지는 건드리지 않음."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "user", "content": "Hello"},
            ],
            thinking={"type": "enabled", "budget_tokens": 128},
        )

        ensure_thinking_prefix(request)

        assert request.messages[0].content == "Hello"


# =============================================================================
# remove_invalid_redacted_thinking 테스트
# =============================================================================


class TestRemoveInvalidRedactedThinking:
    """remove_invalid_redacted_thinking 함수 테스트."""

    def test_removes_empty_string_data(self) -> None:
        """빈 문자열 data를 가진 redacted_thinking 제거."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "redacted_thinking", "data": ""},
                        {"type": "text", "text": "Answer"},
                    ],
                }
            ],
        )

        remove_invalid_redacted_thinking(request)

        assistant_content = request.messages[0].content
        assert len(assistant_content) == 1
        assert assistant_content[0] == {"type": "text", "text": "Answer"}

    def test_removes_non_string_data(self) -> None:
        """비문자열 data를 가진 redacted_thinking 제거."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "redacted_thinking", "data": {"redacted": True}},
                        {"type": "text", "text": "Answer"},
                    ],
                }
            ],
        )

        remove_invalid_redacted_thinking(request)

        assistant_content = request.messages[0].content
        assert len(assistant_content) == 1
        assert assistant_content[0] == {"type": "text", "text": "Answer"}

    def test_removes_none_data(self) -> None:
        """None data를 가진 redacted_thinking 제거."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "redacted_thinking", "data": None},
                        {"type": "text", "text": "Answer"},
                    ],
                }
            ],
        )

        remove_invalid_redacted_thinking(request)

        assistant_content = request.messages[0].content
        assert len(assistant_content) == 1
        assert assistant_content[0] == {"type": "text", "text": "Answer"}

    def test_removes_missing_data_key(self) -> None:
        """data 키가 없는 redacted_thinking 제거."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "redacted_thinking"},
                        {"type": "text", "text": "Answer"},
                    ],
                }
            ],
        )

        remove_invalid_redacted_thinking(request)

        assistant_content = request.messages[0].content
        assert len(assistant_content) == 1
        assert assistant_content[0] == {"type": "text", "text": "Answer"}

    def test_keeps_valid_redacted_thinking(self) -> None:
        """유효한 redacted_thinking은 유지."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "redacted_thinking", "data": "encrypted_data_here"},
                        {"type": "text", "text": "Answer"},
                    ],
                }
            ],
        )

        remove_invalid_redacted_thinking(request)

        assistant_content = request.messages[0].content
        assert len(assistant_content) == 2
        assert assistant_content[0]["type"] == "redacted_thinking"
        assert assistant_content[0]["data"] == "encrypted_data_here"

    def test_keeps_valid_thinking_block(self) -> None:
        """유효한 thinking 블록은 유지."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "Thought", "signature": "sig"},
                        {"type": "text", "text": "Answer"},
                    ],
                }
            ],
        )

        remove_invalid_redacted_thinking(request)

        assistant_content = request.messages[0].content
        assert len(assistant_content) == 2
        assert assistant_content[0]["type"] == "thinking"

    def test_handles_string_content(self) -> None:
        """문자열 content는 그대로 유지."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "assistant", "content": "World"},
            ],
        )

        remove_invalid_redacted_thinking(request)

        assert request.messages[0].content == "World"

    def test_handles_user_messages(self) -> None:
        """user 메시지는 건드리지 않음."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
            ],
        )

        remove_invalid_redacted_thinking(request)

        assert request.messages[0].content == [{"type": "text", "text": "Hello"}]


# =============================================================================
# should_drop_thinking_param 테스트
# =============================================================================


class TestShouldDropThinkingParam:
    """should_drop_thinking_param 함수 테스트."""

    def test_returns_false_when_thinking_is_none(self) -> None:
        """thinking이 None이면 False 반환."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "assistant", "content": "World"},
            ],
            thinking=None,
        )

        assert should_drop_thinking_param(request) is False

    def test_returns_false_when_no_assistant_with_tool_use(self) -> None:
        """tool_use가 있는 assistant 메시지가 없으면 False 반환."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "World"},
            ],
            thinking={"type": "enabled", "budget_tokens": 128},
        )

        assert should_drop_thinking_param(request) is False

    def test_returns_true_when_tool_use_without_thinking(self) -> None:
        """tool_use가 있는데 thinking 블록이 없으면 True 반환."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Let me calculate"},
                        {
                            "type": "tool_use",
                            "id": "tool_1",
                            "name": "calculator",
                            "input": {"x": 1},
                        },
                    ],
                },
            ],
            thinking={"type": "enabled", "budget_tokens": 128},
        )

        assert should_drop_thinking_param(request) is True

    def test_returns_false_when_tool_use_with_thinking(self) -> None:
        """tool_use가 있고 thinking 블록도 있으면 False 반환."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "Thought", "signature": "sig"},
                        {"type": "text", "text": "Let me calculate"},
                        {
                            "type": "tool_use",
                            "id": "tool_1",
                            "name": "calculator",
                            "input": {"x": 1},
                        },
                    ],
                },
            ],
            thinking={"type": "enabled", "budget_tokens": 128},
        )

        assert should_drop_thinking_param(request) is False

    def test_returns_false_when_tool_use_with_redacted_thinking(self) -> None:
        """tool_use가 있고 redacted_thinking 블록이 있으면 False 반환."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "redacted_thinking", "data": "encrypted"},
                        {"type": "text", "text": "Let me calculate"},
                        {
                            "type": "tool_use",
                            "id": "tool_1",
                            "name": "calculator",
                            "input": {"x": 1},
                        },
                    ],
                },
            ],
            thinking={"type": "enabled", "budget_tokens": 128},
        )

        assert should_drop_thinking_param(request) is False

    def test_checks_last_assistant_with_tool_use(self) -> None:
        """마지막 tool_use가 있는 assistant 메시지를 체크."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "user", "content": "Hello"},
                # 첫 번째 assistant: tool_use + thinking 있음
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "Thought", "signature": "sig"},
                        {
                            "type": "tool_use",
                            "id": "tool_1",
                            "name": "calculator",
                            "input": {"x": 1},
                        },
                    ],
                },
                {"role": "user", "content": "Thanks"},
                # 두 번째 assistant: tool_use만 있고 thinking 없음
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tool_2",
                            "name": "calculator",
                            "input": {"x": 2},
                        },
                    ],
                },
            ],
            thinking={"type": "enabled", "budget_tokens": 128},
        )

        # 마지막 assistant with tool_use에 thinking 없으므로 True
        assert should_drop_thinking_param(request) is True

    def test_handles_string_content_with_no_tool_use(self) -> None:
        """문자열 content(tool_use 없음)는 False 반환."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "World"},
            ],
            thinking={"type": "enabled", "budget_tokens": 128},
        )

        assert should_drop_thinking_param(request) is False


# =============================================================================
# 통합 테스트
# =============================================================================


class TestIntegration:
    """통합 테스트."""

    def test_full_flow_removes_invalid_and_moves_valid(self) -> None:
        """invalid 제거 후 valid thinking 이동."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "redacted_thinking", "data": ""},  # invalid - 제거됨
                        {"type": "text", "text": "Answer"},
                        {"type": "thinking", "thinking": "Thought", "signature": "sig"},
                    ],
                }
            ],
            thinking={"type": "enabled", "budget_tokens": 256},
        )

        # 1. invalid 제거
        remove_invalid_redacted_thinking(request)
        # 2. thinking 앞으로 이동
        ensure_thinking_prefix(request)

        assistant_content = request.messages[0].content
        assert len(assistant_content) == 2
        assert assistant_content[0]["type"] == "thinking"
        assert assistant_content[1] == {"type": "text", "text": "Answer"}

    def test_full_flow_with_tool_use_no_thinking_drops_param(self) -> None:
        """tool_use가 있는데 thinking이 없으면 param 드롭 권장."""
        request = AnthropicRequest(
            model="claude-test",
            messages=[
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Let me calculate"},
                        {
                            "type": "tool_use",
                            "id": "tool_1",
                            "name": "calculator",
                            "input": {"x": 1},
                        },
                    ],
                }
            ],
            thinking={"type": "enabled", "budget_tokens": 128},
        )

        # should_drop_thinking_param이 True면 호출자가 thinking을 드롭해야 함
        assert should_drop_thinking_param(request) is True
