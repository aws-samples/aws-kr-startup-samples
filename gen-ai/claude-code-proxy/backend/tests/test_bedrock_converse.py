import pytest

from domain import AnthropicRequest
from bedrock_converse import (
    StreamState,
    _convert_converse_event,
    build_converse_request,
    parse_converse_response,
)


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


def test_parse_converse_response_text_and_tools():
    data = {
        "id": "resp_1",
        "stopReason": "end_turn",
        "usage": {
            "inputTokens": 10,
            "outputTokens": 5,
            "cacheReadInputTokens": 2,
            "cacheCreationInputTokens": 1,
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
        {"metadata": {"usage": {"outputTokens": 5}}},
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
