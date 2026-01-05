from domain import AnthropicRequest
from thinking_normalizer import ensure_thinking_prefix


def test_ensure_thinking_prefix_inserts_redacted_block() -> None:
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "World"},
        ],
        thinking={"type": "enabled", "budget_tokens": 128},
    )

    ensure_thinking_prefix(request)

    assistant_content = request.messages[1].content
    assert assistant_content[0]["type"] == "redacted_thinking"
    assert assistant_content[1] == {"type": "text", "text": "World"}


def test_ensure_thinking_prefix_moves_existing_thinking() -> None:
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
