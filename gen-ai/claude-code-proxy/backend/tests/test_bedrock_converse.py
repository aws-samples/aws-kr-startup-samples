import pytest
from bedrock_converse import (
    StreamState,
    _convert_converse_event,
    build_converse_request,
    parse_converse_response,
)

from domain import AnthropicRequest


def test_build_converse_request_basic():
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "Hello"}],
        system="System prompt",
        max_tokens=256,
        temperature=0.2,
        top_p=0.9,
        top_k=5,
        stop_sequences=["\n\n"],
    )

    payload = build_converse_request(request)

    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == [{"text": "Hello"}]
    assert payload["system"] == [{"text": "System prompt"}]
    assert payload["inferenceConfig"]["maxTokens"] == 256
    assert payload["inferenceConfig"]["temperature"] == 0.2
    assert payload["inferenceConfig"]["topP"] == 0.9
    assert payload["inferenceConfig"]["topK"] == 5
    assert payload["inferenceConfig"]["stopSequences"] == ["\n\n"]


def test_build_converse_request_tools_and_choice():
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "Use tool"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Do math",
                    "parameters": {"type": "object", "properties": {"x": {"type": "number"}}},
                },
            }
        ],
        tool_choice={"type": "auto"},
    )

    payload = build_converse_request(request)
    tool_config = payload["toolConfig"]

    assert tool_config["tools"][0]["toolSpec"]["name"] == "calculator"
    assert tool_config["tools"][0]["toolSpec"]["description"] == "Do math"
    assert tool_config["tools"][0]["toolSpec"]["inputSchema"]["json"]["type"] == "object"
    assert tool_config["toolChoice"] == {"auto": {}}


def test_build_converse_request_metadata_limit_and_filter():
    metadata = {"k0": "v0", "bad": 1}
    metadata.update({f"k{i}": f"v{i}" for i in range(1, 20)})

    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "Hello"}],
        metadata=metadata,
    )

    payload = build_converse_request(request)
    request_metadata = payload["requestMetadata"]

    assert "bad" not in request_metadata
    assert len(request_metadata) == 16


def test_build_converse_request_thinking_fields():
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "Hello"}],
        thinking={"type": "enabled", "budget_tokens": 128},
    )

    payload = build_converse_request(request)

    assert payload["additionalModelRequestFields"]["thinking"] == {
        "type": "enabled",
        "budget_tokens": 128,
    }


def test_build_converse_request_thinking_blocks():
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "Let me think.",
                        "signature": "sig-123",
                    },
                    {"type": "redacted_thinking", "data": "redacted"},
                    {"type": "text", "text": "Answer"},
                ],
            }
        ],
    )

    payload = build_converse_request(request)

    content = payload["messages"][0]["content"]
    assert content[0] == {
        "reasoningContent": {"reasoningText": {"text": "Let me think.", "signature": "sig-123"}}
    }
    assert content[1] == {"reasoningContent": {"redactedContent": "redacted"}}
    assert content[2] == {"text": "Answer"}


def test_parse_converse_response_text_and_tools():
    data = {
        "id": "resp_1",
        "stopReason": "end_turn",
        "usage": {
            "inputTokens": 10,
            "outputTokens": 5,
            "cacheReadInputTokens": 2,
            "cacheWriteInputTokens": 1,
        },
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {"text": "Hello"},
                    {
                        "toolUse": {
                            "toolUseId": "tool_1",
                            "name": "calculator",
                            "input": {"x": 1},
                        }
                    },
                    {
                        "toolResult": {
                            "toolUseId": "tool_1",
                            "status": "success",
                            "content": [{"text": "2"}],
                        }
                    },
                ],
            }
        },
    }

    response, usage = parse_converse_response(data, model="claude-test")

    assert response.id == "resp_1"
    assert response.stop_reason == "end_turn"
    assert usage.input_tokens == 10
    assert usage.output_tokens == 5
    assert usage.cache_read_input_tokens == 2
    assert usage.cache_creation_input_tokens == 1
    assert response.content[0] == {"type": "text", "text": "Hello"}
    assert response.content[1]["type"] == "tool_use"
    assert response.content[2]["type"] == "tool_result"
    assert response.content[2]["content"] == [{"type": "text", "text": "2"}]


def test_parse_converse_response_thinking_blocks():
    data = {
        "id": "resp_2",
        "stopReason": "end_turn",
        "usage": {"inputTokens": 5, "outputTokens": 3},
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "reasoningContent": {
                            "reasoningText": {
                                "text": "Let me think.",
                                "signature": "sig-123",
                            }
                        }
                    },
                    {"reasoningContent": {"redactedContent": {"redacted": True}}},
                    {"text": "Answer"},
                ],
            }
        },
    }

    response, usage = parse_converse_response(data, model="claude-test")

    assert usage.input_tokens == 5
    assert usage.output_tokens == 3
    assert response.content[0] == {
        "type": "thinking",
        "thinking": "Let me think.",
        "signature": "sig-123",
    }
    assert response.content[1] == {
        "type": "redacted_thinking",
        "data": {"redacted": True},
    }
    assert response.content[2] == {"type": "text", "text": "Answer"}


@pytest.mark.asyncio
async def test_stream_event_translation_end_turn_with_usage():
    state = StreamState(message_id="msg_test")
    model = "claude-test"

    events = []
    for event in [
        {"messageStart": {"conversationId": "conv1"}},
        {
            "contentBlockStart": {
                "contentBlockIndex": 0,
                "start": {"text": ""},
            }
        },
        {
            "contentBlockDelta": {
                "contentBlockIndex": 0,
                "delta": {"text": "Hi"},
            }
        },
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "end_turn"}},
        {"metadata": {"usage": {"inputTokens": 100, "outputTokens": 5}}},
    ]:
        async for payload in _convert_converse_event(event, state, model):
            events.append(payload)

    assert events[0]["type"] == "message_start"
    assert events[0]["message"]["id"] == "msg_test"
    assert events[1]["type"] == "content_block_start"
    assert events[2]["type"] == "content_block_delta"
    assert events[3]["type"] == "content_block_stop"
    assert events[4]["type"] == "message_delta"
    assert events[4]["delta"]["stop_reason"] == "end_turn"
    assert events[4]["usage"]["input_tokens"] == 100
    assert events[4]["usage"]["output_tokens"] == 5
    assert events[5]["type"] == "message_stop"


@pytest.mark.asyncio
async def test_stream_event_translation_thinking_blocks():
    state = StreamState(message_id="msg_test")
    model = "claude-test"

    events = []
    for event in [
        {"messageStart": {"conversationId": "conv1"}},
        {
            "contentBlockStart": {
                "contentBlockIndex": 0,
                "start": {"reasoningContent": {"text": ""}},
            }
        },
        {
            "contentBlockDelta": {
                "contentBlockIndex": 0,
                "delta": {"reasoningContent": {"text": "Let me think"}},
            }
        },
        {
            "contentBlockDelta": {
                "contentBlockIndex": 0,
                "delta": {"reasoningContent": {"signature": "sig-456"}},
            }
        },
        {"contentBlockStop": {"contentBlockIndex": 0}},
    ]:
        async for payload in _convert_converse_event(event, state, model):
            events.append(payload)

    assert events[0]["type"] == "message_start"
    assert events[1]["type"] == "content_block_start"
    assert events[1]["content_block"]["type"] == "thinking"
    assert events[2]["type"] == "content_block_delta"
    assert events[2]["delta"] == {"type": "thinking_delta", "thinking": "Let me think"}
    assert events[3]["type"] == "content_block_delta"
    assert events[3]["delta"] == {"type": "signature_delta", "signature": "sig-456"}
    assert events[4]["type"] == "content_block_stop"


@pytest.mark.asyncio
async def test_stream_event_translation_redacted_thinking():
    state = StreamState(message_id="msg_test")
    model = "claude-test"

    events = []
    event = {
        "contentBlockStart": {
            "contentBlockIndex": 0,
            "start": {"reasoningContent": {"redactedContent": {"redacted": True}}},
        }
    }
    async for payload in _convert_converse_event(event, state, model):
        events.append(payload)

    assert events[0]["type"] == "content_block_start"
    assert events[0]["content_block"] == {
        "type": "redacted_thinking",
        "data": {"redacted": True},
    }


# =============================================================================
# Cache Control Tests - Content Block
# =============================================================================


def test_build_converse_request_content_with_cache_control():
    """Single text block with cache_control should add cachePoint after it."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Long context to cache...",
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        ],
    )

    payload = build_converse_request(request)
    content = payload["messages"][0]["content"]

    assert len(content) == 2
    assert content[0] == {"text": "Long context to cache..."}
    assert content[1] == {"cachePoint": {"type": "default"}}


def test_build_converse_request_multiple_content_blocks_with_cache_control():
    """Multiple blocks where only some have cache_control."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "First block"},
                    {
                        "type": "text",
                        "text": "Second block to cache",
                        "cache_control": {"type": "ephemeral"},
                    },
                    {"type": "text", "text": "Third block"},
                ],
            }
        ],
    )

    payload = build_converse_request(request)
    content = payload["messages"][0]["content"]

    assert len(content) == 4
    assert content[0] == {"text": "First block"}
    assert content[1] == {"text": "Second block to cache"}
    assert content[2] == {"cachePoint": {"type": "default"}}
    assert content[3] == {"text": "Third block"}


def test_build_converse_request_content_without_cache_control_unchanged():
    """Content without cache_control should not have cachePoint."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "No cache control here"},
                ],
            }
        ],
    )

    payload = build_converse_request(request)
    content = payload["messages"][0]["content"]

    assert len(content) == 1
    assert content[0] == {"text": "No cache control here"}


# =============================================================================
# Cache Control Tests - System Prompt
# =============================================================================


def test_build_converse_request_system_string_no_cache():
    """String system prompt cannot have cache_control."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "Hello"}],
        system="Simple string system prompt",
    )

    payload = build_converse_request(request)

    assert payload["system"] == [{"text": "Simple string system prompt"}]


def test_build_converse_request_system_block_with_cache_control():
    """System block with cache_control should add cachePoint."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "Hello"}],
        system=[
            {
                "type": "text",
                "text": "System instructions to cache",
                "cache_control": {"type": "ephemeral"},
            }
        ],
    )

    payload = build_converse_request(request)

    assert len(payload["system"]) == 2
    assert payload["system"][0] == {"text": "System instructions to cache"}
    assert payload["system"][1] == {"cachePoint": {"type": "default"}}


def test_build_converse_request_system_multiple_blocks_selective_cache():
    """Multiple system blocks with selective cache_control."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "Hello"}],
        system=[
            {"type": "text", "text": "Instructions part 1"},
            {
                "type": "text",
                "text": "Instructions part 2 to cache",
                "cache_control": {"type": "ephemeral"},
            },
        ],
    )

    payload = build_converse_request(request)

    assert len(payload["system"]) == 3
    assert payload["system"][0] == {"text": "Instructions part 1"}
    assert payload["system"][1] == {"text": "Instructions part 2 to cache"}
    assert payload["system"][2] == {"cachePoint": {"type": "default"}}


# =============================================================================
# Cache Control Tests - Tools
# =============================================================================


def test_build_converse_request_tool_with_cache_control():
    """Single tool with cache_control should add cachePoint after it."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "Use the tool"}],
        tools=[
            {
                "name": "get_weather",
                "description": "Get weather info",
                "input_schema": {"type": "object", "properties": {}},
                "cache_control": {"type": "ephemeral"},
            }
        ],
    )

    payload = build_converse_request(request)
    tools = payload["toolConfig"]["tools"]

    assert len(tools) == 2
    assert tools[0]["toolSpec"]["name"] == "get_weather"
    assert tools[1] == {"cachePoint": {"type": "default"}}


def test_build_converse_request_multiple_tools_with_cache_control():
    """Multiple tools where only the last one has cache_control."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "Use tools"}],
        tools=[
            {
                "name": "tool_a",
                "description": "First tool",
                "input_schema": {"type": "object"},
            },
            {
                "name": "tool_b",
                "description": "Second tool with cache",
                "input_schema": {"type": "object"},
                "cache_control": {"type": "ephemeral"},
            },
        ],
    )

    payload = build_converse_request(request)
    tools = payload["toolConfig"]["tools"]

    assert len(tools) == 3
    assert tools[0]["toolSpec"]["name"] == "tool_a"
    assert tools[1]["toolSpec"]["name"] == "tool_b"
    assert tools[2] == {"cachePoint": {"type": "default"}}


def test_build_converse_request_tool_without_cache_control():
    """Tool without cache_control should not have cachePoint."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[{"role": "user", "content": "Use tool"}],
        tools=[
            {
                "name": "simple_tool",
                "description": "No cache control",
                "input_schema": {"type": "object"},
            }
        ],
    )

    payload = build_converse_request(request)
    tools = payload["toolConfig"]["tools"]

    assert len(tools) == 1
    assert tools[0]["toolSpec"]["name"] == "simple_tool"


# =============================================================================
# Cache Control Tests - Complex Scenarios
# =============================================================================


def test_build_converse_request_cache_control_in_all_fields():
    """cache_control in system, messages, and tools all at once."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "User message to cache",
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        ],
        system=[
            {
                "type": "text",
                "text": "System prompt to cache",
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[
            {
                "name": "cached_tool",
                "description": "Tool to cache",
                "input_schema": {"type": "object"},
                "cache_control": {"type": "ephemeral"},
            }
        ],
    )

    payload = build_converse_request(request)

    # Check system: 1 text block + 1 cachePoint
    assert len(payload["system"]) == 2
    assert payload["system"][1] == {"cachePoint": {"type": "default"}}

    # Check messages: 1 text block + 1 cachePoint
    assert len(payload["messages"][0]["content"]) == 2
    assert payload["messages"][0]["content"][1] == {"cachePoint": {"type": "default"}}

    # Check tools: 1 tool + 1 cachePoint
    assert len(payload["toolConfig"]["tools"]) == 2
    assert payload["toolConfig"]["tools"][1] == {"cachePoint": {"type": "default"}}


def test_build_converse_request_max_cache_points():
    """Test scenario with 4 cache points (max allowed by Bedrock)."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "First cached block",
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": "Second cached block",
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
            }
        ],
        system=[
            {
                "type": "text",
                "text": "System to cache",
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[
            {
                "name": "tool",
                "description": "Cached tool",
                "input_schema": {"type": "object"},
                "cache_control": {"type": "ephemeral"},
            }
        ],
    )

    payload = build_converse_request(request)

    # Count total cachePoints
    cache_points = 0
    for block in payload.get("system", []):
        if "cachePoint" in block:
            cache_points += 1
    for msg in payload.get("messages", []):
        for block in msg.get("content", []):
            if "cachePoint" in block:
                cache_points += 1
    if "toolConfig" in payload:
        for block in payload["toolConfig"].get("tools", []):
            if "cachePoint" in block:
                cache_points += 1

    assert cache_points == 4


# =============================================================================
# Cache Control Tests - Over Max
# =============================================================================


def test_build_converse_request_cache_points_capped():
    """Cache points should be capped at 4 even if more blocks request caching."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Cached 1",
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": "Cached 2",
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
            }
        ],
        system=[
            {
                "type": "text",
                "text": "Cached 3",
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[
            {
                "name": "tool_1",
                "description": "Cached 4",
                "input_schema": {"type": "object"},
                "cache_control": {"type": "ephemeral"},
            },
            {
                "name": "tool_2",
                "description": "Cached 5",
                "input_schema": {"type": "object"},
                "cache_control": {"type": "ephemeral"},
            },
        ],
    )

    payload = build_converse_request(request)

    cache_points = 0
    for block in payload.get("system", []):
        if "cachePoint" in block:
            cache_points += 1
    for msg in payload.get("messages", []):
        for block in msg.get("content", []):
            if "cachePoint" in block:
                cache_points += 1
    if "toolConfig" in payload:
        for block in payload["toolConfig"].get("tools", []):
            if "cachePoint" in block:
                cache_points += 1

    assert cache_points == 4
# =============================================================================
# Cache Control Tests - Edge Cases
# =============================================================================


def test_build_converse_request_cache_control_empty_type():
    """Empty cache_control dict should not add cachePoint."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Block with empty cache_control",
                        "cache_control": {},
                    }
                ],
            }
        ],
    )

    payload = build_converse_request(request)
    content = payload["messages"][0]["content"]

    assert len(content) == 1
    assert content[0] == {"text": "Block with empty cache_control"}


def test_build_converse_request_cache_control_none_value():
    """cache_control: None should not add cachePoint."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Block with None cache_control",
                        "cache_control": None,
                    }
                ],
            }
        ],
    )

    payload = build_converse_request(request)
    content = payload["messages"][0]["content"]

    assert len(content) == 1
    assert content[0] == {"text": "Block with None cache_control"}


def test_build_converse_request_cache_control_invalid_type():
    """cache_control with invalid type should not add cachePoint."""
    request = AnthropicRequest(
        model="claude-test",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Block with invalid type",
                        "cache_control": {"type": "invalid"},
                    }
                ],
            }
        ],
    )

    payload = build_converse_request(request)
    content = payload["messages"][0]["content"]

    assert len(content) == 1
    assert content[0] == {"text": "Block with invalid type"}


# =============================================================================
# Cache Token Response Parsing Tests
# =============================================================================


def test_parse_converse_response_cache_tokens_zero():
    """Response with zero cache tokens."""
    data = {
        "id": "resp_cache_zero",
        "stopReason": "end_turn",
        "usage": {
            "inputTokens": 100,
            "outputTokens": 50,
            "cacheReadInputTokens": 0,
            "cacheWriteInputTokens": 0,
        },
        "output": {"message": {"role": "assistant", "content": [{"text": "Response"}]}},
    }

    response, usage = parse_converse_response(data, model="claude-test")

    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.cache_read_input_tokens == 0
    assert usage.cache_creation_input_tokens == 0


def test_parse_converse_response_cache_tokens_legacy_field():
    """Response with legacy cacheCreationInputTokens should still be parsed."""
    data = {
        "id": "resp_cache_legacy",
        "stopReason": "end_turn",
        "usage": {
            "inputTokens": 100,
            "outputTokens": 50,
            "cacheReadInputTokens": 3,
            "cacheCreationInputTokens": 2,
        },
        "output": {"message": {"role": "assistant", "content": [{"text": "Response"}]}},
    }

    response, usage = parse_converse_response(data, model="claude-test")

    assert usage.cache_read_input_tokens == 3
    assert usage.cache_creation_input_tokens == 2


def test_parse_converse_response_cache_tokens_none():
    """Response without cache token fields (pre-caching or non-cached request)."""
    data = {
        "id": "resp_no_cache",
        "stopReason": "end_turn",
        "usage": {
            "inputTokens": 100,
            "outputTokens": 50,
            # No cacheReadInputTokens or cacheWriteInputTokens
        },
        "output": {"message": {"role": "assistant", "content": [{"text": "Response"}]}},
    }

    response, usage = parse_converse_response(data, model="claude-test")

    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.cache_read_input_tokens is None
    assert usage.cache_creation_input_tokens is None


@pytest.mark.asyncio
async def test_stream_event_cache_tokens():
    """Streaming response should include cache tokens in usage."""
    state = StreamState(message_id="msg_cache_stream")
    model = "claude-test"

    events = []
    for event in [
        {"messageStart": {"conversationId": "conv1"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {"text": ""}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": "Hi"}}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "end_turn"}},
        {
            "metadata": {
                "usage": {
                    "inputTokens": 500,
                    "outputTokens": 10,
                    "cacheReadInputTokens": 400,
                    "cacheWriteInputTokens": 50,
                }
            }
        },
    ]:
        async for payload in _convert_converse_event(event, state, model):
            events.append(payload)

    # Find the message_delta event with usage
    message_delta = next(e for e in events if e.get("type") == "message_delta")

    assert message_delta["usage"]["input_tokens"] == 500
    assert message_delta["usage"]["output_tokens"] == 10
    assert message_delta["usage"]["cache_read_input_tokens"] == 400
    assert message_delta["usage"]["cache_creation_input_tokens"] == 50


@pytest.mark.asyncio
async def test_stream_event_cache_tokens_legacy_field():
    """Streaming response should accept legacy cacheCreationInputTokens."""
    state = StreamState(message_id="msg_cache_stream_legacy")
    model = "claude-test"

    events = []
    for event in [
        {"messageStart": {"conversationId": "conv1"}},
        {"messageStop": {"stopReason": "end_turn"}},
        {
            "metadata": {
                "usage": {
                    "inputTokens": 200,
                    "outputTokens": 20,
                    "cacheReadInputTokens": 120,
                    "cacheCreationInputTokens": 30,
                }
            }
        },
    ]:
        async for payload in _convert_converse_event(event, state, model):
            events.append(payload)

    message_delta = next(e for e in events if e.get("type") == "message_delta")

    assert message_delta["usage"]["cache_read_input_tokens"] == 120
    assert message_delta["usage"]["cache_creation_input_tokens"] == 30
