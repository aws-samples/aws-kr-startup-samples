from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import logging
import json
import os
import httpx
import traceback

from models import MessagesRequest
from config import (
    BEDROCK_FALLBACK_ENABLED,
    RATE_LIMIT_TRACKING_ENABLED,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Import these from main to avoid circular dependency
# These will be injected when router is included
_check_rate_limit_status = None
_store_rate_limit_status = None
_call_bedrock_api = None
_mask_api_key = None


def set_dependencies(check_rate_limit, store_rate_limit, call_bedrock, mask_key):
    global \
        _check_rate_limit_status, \
        _store_rate_limit_status, \
        _call_bedrock_api, \
        _mask_api_key
    _check_rate_limit_status = check_rate_limit
    _store_rate_limit_status = store_rate_limit
    _call_bedrock_api = call_bedrock
    _mask_api_key = mask_key


@router.post("/v1/messages")
@router.post("/user/{user_id}/v1/messages")
async def create_message(
    request: MessagesRequest, raw_request: Request, user_id: str = "default"
):
    """
    Anthropic Messages API 프록시 엔드포인트
    """
    logger.info("=" * 80)
    logger.info(f"📥 [REQUEST] New /v1/messages request received from user: {user_id}")

    logger.info("📋 [HEADERS] Request headers:")
    for header_name, header_value in raw_request.headers.items():
        if header_name.lower() in ["x-api-key", "authorization"]:
            logger.info(f"   {header_name}: {_mask_api_key(header_value)}")
        else:
            logger.info(f"   {header_name}: {header_value}")

    logger.info(f"📦 [BODY] Request body:")
    logger.info(f"   Model: {request.model}")
    logger.info(f"   Max Tokens: {request.max_tokens}")
    logger.info(f"   Messages Count: {len(request.messages)}")
    logger.info(f"   Stream: {request.stream}")
    logger.info(f"   Temperature: {request.temperature}")
    if request.system:
        logger.info(
            f"   System Prompt: {'Yes (string)' if isinstance(request.system, str) else f'Yes ({len(request.system)} parts)'}"
        )
    if request.tools:
        logger.info(f"   Tools: {len(request.tools)} tools provided")
    if request.thinking:
        logger.info(f"   Thinking: Enabled")

    try:
        header_api_key = raw_request.headers.get("x-api-key")

        auth_header = raw_request.headers.get(
            "authorization"
        ) or raw_request.headers.get("Authorization")
        bearer_token = None
        if auth_header and auth_header.startswith("Bearer "):
            bearer_token = auth_header.replace("Bearer ", "").strip()

        env_api_key = os.getenv("ANTHROPIC_API_KEY")
        env_auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")

        use_bearer_auth = False

        if header_api_key:
            api_key = header_api_key
            auth_source = f"x-api-key header: {_mask_api_key(header_api_key)}"
            use_bearer_auth = False
        elif bearer_token:
            api_key = bearer_token
            auth_source = f"Authorization Bearer header (Claude Code subscription): {_mask_api_key(bearer_token)}"
            use_bearer_auth = True
        elif env_api_key:
            api_key = env_api_key
            auth_source = (
                f"ANTHROPIC_API_KEY environment variable: {_mask_api_key(env_api_key)}"
            )
            use_bearer_auth = False
        elif env_auth_token:
            api_key = env_auth_token
            auth_source = f"ANTHROPIC_AUTH_TOKEN environment variable (Claude Code): {_mask_api_key(env_auth_token)}"
            use_bearer_auth = True
        else:
            api_key = None
            auth_source = "None"

        logger.info(f"🔑 [AUTH] Using API key from {auth_source}")

        request_data = request.model_dump(exclude_none=True, exclude={"original_model"})

        if request.thinking is not None:
            request_data["thinking"] = request.thinking.model_dump(exclude_none=True)

        if RATE_LIMIT_TRACKING_ENABLED:
            is_rate_limited, remaining_seconds = await _check_rate_limit_status(user_id)
            if is_rate_limited:
                logger.info(
                    f"⏳ [RATE LIMIT CHECK] User {user_id} is rate limited for {remaining_seconds}s"
                )

                if BEDROCK_FALLBACK_ENABLED:
                    logger.info("🔄 [FALLBACK] Using Bedrock (stored rate limit)")
                    try:
                        bedrock_response = await _call_bedrock_api(
                            request_data,
                            request.model,
                            stream=request.stream,
                            user_id=user_id,
                        )

                        if request.stream:
                            return bedrock_response
                        else:
                            logger.info(
                                "✅ [BEDROCK FALLBACK] Successfully received response from Bedrock (via stored rate limit)"
                            )
                            logger.info(
                                "📤 [RESPONSE] Returning Bedrock response to client"
                            )
                            logger.info("=" * 80)

                            try:
                                with open("response.json", "a") as f:
                                    json.dump(bedrock_response, f, indent=2)
                                    f.write("\n")
                            except Exception as e:
                                logger.warning(
                                    f"Could not write Bedrock response to response.json: {e}"
                                )

                            return bedrock_response

                    except Exception as bedrock_error:
                        logger.error(
                            f"❌ [BEDROCK FALLBACK ERROR] Bedrock fallback failed: {bedrock_error}"
                        )
                else:
                    logger.warning(
                        "⚠️ [RATE LIMIT] User is rate limited but Bedrock fallback is disabled"
                    )
            else:
                logger.debug(
                    f"✅ [RATE LIMIT CHECK] User {user_id} is not currently rate limited"
                )

        if not api_key:
            logger.error("❌ [AUTH] Missing API key")
            logger.error("Please provide x-api-key header with your Anthropic API key:")
            logger.error("   curl -H 'x-api-key: sk-ant-...' ...")
            raise HTTPException(
                status_code=401,
                detail={
                    "type": "error",
                    "error": {
                        "type": "authentication_error",
                        "message": "Missing API key. Please provide x-api-key header with your Anthropic API key.",
                    },
                },
            )

        api_base = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com")
        api_url = f"{api_base}/v1/messages"

        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        if use_bearer_auth:
            headers["Authorization"] = f"Bearer {api_key}"
            logger.info(f"   Using Authorization Bearer header for authentication")
        else:
            headers["x-api-key"] = api_key
            logger.info(f"   Using x-api-key header for authentication")

        if "anthropic-beta" in raw_request.headers:
            headers["anthropic-beta"] = raw_request.headers["anthropic-beta"]
            logger.info(
                f"   anthropic-beta header: {raw_request.headers['anthropic-beta']}"
            )

        logger.info(f"🚀 [FORWARD] Forwarding request to Anthropic API")
        logger.info(f"   Target URL: {api_url}")
        logger.info(f"📋 [FORWARD HEADERS] Headers being sent to Anthropic:")
        for header_name, header_value in headers.items():
            if header_name.lower() in ["x-api-key", "authorization"]:
                logger.info(f"   {header_name}: {_mask_api_key(header_value)}")
            else:
                logger.info(f"   {header_name}: {header_value}")
        logger.debug(f"   Full request data: {json.dumps(request_data, indent=2)}")

        async with httpx.AsyncClient(timeout=600.0) as client:
            if os.getenv("FORCE_RATE_LIMIT", "false").lower() == "true":
                logger.warning("🧪 [TEST MODE] Simulating 429 rate limit error")

                retry_after_seconds = 60
                logger.info(
                    f"⏱️ [RATE LIMIT] retry-after: {retry_after_seconds} seconds for user {user_id}"
                )

                await _store_rate_limit_status(user_id, retry_after_seconds)

                if BEDROCK_FALLBACK_ENABLED:
                    logger.info(
                        "🔄 [FALLBACK] Simulated 429, attempting Bedrock fallback"
                    )
                    try:
                        bedrock_response = await _call_bedrock_api(
                            request_data,
                            request.model,
                            stream=request.stream,
                            user_id=user_id,
                        )

                        if request.stream:

                            async def bedrock_stream_generator():
                                try:
                                    for event in bedrock_response["body"]:
                                        chunk = event.get("chunk", {})
                                        if chunk:
                                            chunk_bytes = chunk.get("bytes", b"")
                                            if chunk_bytes:
                                                chunk_data = json.loads(
                                                    chunk_bytes.decode()
                                                )
                                                if (
                                                    chunk_data.get("type")
                                                    == "content_block_delta"
                                                ):
                                                    sse_data = f"data: {json.dumps(chunk_data)}\n\n"
                                                    yield sse_data.encode()
                                                elif (
                                                    chunk_data.get("type")
                                                    == "message_stop"
                                                ):
                                                    sse_data = f"data: {json.dumps(chunk_data)}\n\n"
                                                    yield sse_data.encode()
                                                    break
                                except Exception as e:
                                    logger.error(f"❌ [BEDROCK STREAM ERROR] {e}")
                                    error_event = f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                                    yield error_event.encode()

                            logger.info("✅ [TEST MODE] Bedrock fallback successful")
                            return StreamingResponse(
                                bedrock_stream_generator(),
                                media_type="text/event-stream",
                                headers={
                                    "Cache-Control": "no-cache",
                                    "Connection": "keep-alive",
                                },
                            )
                        else:
                            logger.info("✅ [TEST MODE] Bedrock fallback successful")
                            return bedrock_response
                    except Exception as bedrock_error:
                        logger.error(
                            f"❌ [TEST MODE] Bedrock fallback failed: {bedrock_error}"
                        )
                        raise HTTPException(
                            status_code=503,
                            detail={
                                "type": "error",
                                "error": {
                                    "type": "service_unavailable",
                                    "message": "Both Anthropic (simulated 429) and Bedrock failed",
                                },
                            },
                        )
                else:
                    logger.warning(
                        "⚠️ [TEST MODE] Bedrock fallback disabled, returning 429"
                    )
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "type": "error",
                            "error": {
                                "type": "rate_limit_error",
                                "message": "Rate limit exceeded (simulated)",
                            },
                        },
                    )

            if request.stream:
                logger.info("📡 [STREAM] Streaming request detected")

                streaming_response = await client.send(
                    client.build_request(
                        "POST", api_url, headers=headers, json=request_data
                    ),
                    stream=True,
                )

                if streaming_response.status_code != 200:
                    error_text = await streaming_response.aread()
                    logger.error(
                        f"❌ [ERROR] Anthropic API error: {streaming_response.status_code}"
                    )
                    logger.error(f"📋 [ERROR HEADERS] Response headers from Anthropic:")
                    for header_name, header_value in streaming_response.headers.items():
                        logger.error(f"   {header_name}: {header_value}")
                    logger.error(f"   Error body: {error_text.decode()}")

                    if streaming_response.status_code == 429:
                        retry_after = streaming_response.headers.get("retry-after")
                        retry_after_seconds = int(retry_after) if retry_after else 0

                        logger.info(
                            f"⏱️ [RATE LIMIT] retry-after: {retry_after_seconds} seconds for user {user_id}"
                        )

                        if retry_after_seconds > 0:
                            await _store_rate_limit_status(user_id, retry_after_seconds)

                        if BEDROCK_FALLBACK_ENABLED:
                            logger.info(
                                "🔄 [FALLBACK] Detected 429 rate limit error, attempting Bedrock fallback for streaming request"
                            )
                            try:
                                bedrock_response = await _call_bedrock_api(
                                    request_data,
                                    request.model,
                                    stream=True,
                                    user_id=user_id,
                                )

                                async def bedrock_stream_generator():
                                    try:
                                        for event in bedrock_response["body"]:
                                            chunk = event.get("chunk", {})
                                            if chunk:
                                                chunk_bytes = chunk.get("bytes", b"")
                                                if chunk_bytes:
                                                    chunk_data = json.loads(
                                                        chunk_bytes.decode()
                                                    )
                                                    if (
                                                        chunk_data.get("type")
                                                        == "content_block_delta"
                                                    ):
                                                        sse_data = f"data: {json.dumps(chunk_data)}\n\n"
                                                        yield sse_data.encode()
                                                    elif (
                                                        chunk_data.get("type")
                                                        == "message_stop"
                                                    ):
                                                        sse_data = f"data: {json.dumps(chunk_data)}\n\n"
                                                        yield sse_data.encode()
                                                        break
                                    except Exception as e:
                                        logger.error(
                                            f"❌ [BEDROCK STREAM ERROR] Error in Bedrock streaming: {e}"
                                        )
                                        error_event = f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                                        yield error_event.encode()

                                logger.info(
                                    "✅ [BEDROCK FALLBACK] Successfully switched to Bedrock streaming"
                                )
                                return StreamingResponse(
                                    bedrock_stream_generator(),
                                    media_type="text/event-stream",
                                    headers={
                                        "Cache-Control": "no-cache",
                                        "Connection": "keep-alive",
                                    },
                                )

                            except Exception as bedrock_error:
                                logger.error(
                                    f"❌ [BEDROCK FALLBACK ERROR] Bedrock fallback failed: {bedrock_error}"
                                )
                                print(bedrock_error)

                    try:
                        error_json = json.loads(error_text)
                        raise HTTPException(
                            status_code=streaming_response.status_code,
                            detail=error_json,
                        )
                    except json.JSONDecodeError:
                        raise HTTPException(
                            status_code=streaming_response.status_code,
                            detail={"error": error_text.decode()},
                        )

                logger.info(
                    f"✅ [STREAM] Successfully connected to Anthropic API streaming endpoint"
                )
                logger.info(f"   Status: {streaming_response.status_code}")
                logger.info(f"📤 [RESPONSE] Starting to stream response to client")

                chunk_count = 0

                async def stream_generator():
                    nonlocal chunk_count
                    try:
                        async for chunk in streaming_response.aiter_bytes():
                            chunk_count += 1
                            if chunk_count == 1:
                                logger.debug(
                                    f"   First chunk received (size: {len(chunk)} bytes)"
                                )
                            yield chunk
                        logger.info(
                            f"✅ [STREAM] Streaming completed - {chunk_count} chunks sent"
                        )
                    except Exception as e:
                        logger.warning(f"❌ [STREAM] Error streaming response: {e}")
                        raise
                    finally:
                        await streaming_response.aclose()
                        logger.debug("   Stream closed")

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )

            else:
                logger.info("💬 [NON-STREAM] Non-streaming request")

                response = await client.post(
                    api_url, headers=headers, json=request_data
                )

                if response.status_code != 200:
                    logger.error(
                        f"❌ [ERROR] Anthropic API error: {response.status_code}"
                    )
                    logger.error(f"📋 [ERROR HEADERS] Response headers from Anthropic:")
                    for header_name, header_value in response.headers.items():
                        logger.error(f"   {header_name}: {header_value}")
                    logger.error(f"   Error body: {response.text}")

                    if response.status_code == 429:
                        retry_after = response.headers.get("retry-after")
                        retry_after_seconds = int(retry_after) if retry_after else 0

                        logger.info(
                            f"⏱️ [RATE LIMIT] retry-after: {retry_after_seconds} seconds for user {user_id}"
                        )

                        if retry_after_seconds > 0:
                            await _store_rate_limit_status(user_id, retry_after_seconds)

                        if BEDROCK_FALLBACK_ENABLED:
                            logger.info(
                                "🔄 [FALLBACK] Detected 429 rate limit error, attempting Bedrock fallback"
                            )
                            try:
                                bedrock_response = await _call_bedrock_api(
                                    request_data,
                                    request.model,
                                    stream=False,
                                    user_id=user_id,
                                )

                                logger.info(
                                    "✅ [BEDROCK FALLBACK] Successfully received response from Bedrock"
                                )
                                logger.info(
                                    f"📤 [RESPONSE] Returning Bedrock response to client"
                                )
                                logger.info("=" * 80)

                                try:
                                    with open("response.json", "a") as f:
                                        json.dump(bedrock_response, f, indent=2)
                                        f.write("\n")
                                except Exception as e:
                                    logger.warning(
                                        f"Could not write Bedrock response to response.json: {e}"
                                    )

                                return bedrock_response

                            except Exception as bedrock_error:
                                logger.error(
                                    f"❌ [BEDROCK FALLBACK ERROR] Bedrock fallback failed: {bedrock_error}"
                                )

                    try:
                        error_json = response.json()
                        raise HTTPException(
                            status_code=response.status_code, detail=error_json
                        )
                    except json.JSONDecodeError:
                        raise HTTPException(
                            status_code=response.status_code,
                            detail={"error": response.text},
                        )

                response_json = response.json()

                logger.info(f"✅ [SUCCESS] Received response from Anthropic API")
                logger.info(f"   Status: {response.status_code}")
                logger.info(f"   Response ID: {response_json.get('id', 'N/A')}")
                logger.info(f"   Model: {response_json.get('model', 'N/A')}")
                logger.info(
                    f"   Stop Reason: {response_json.get('stop_reason', 'N/A')}"
                )

                if "usage" in response_json:
                    usage = response_json["usage"]
                    logger.info(f"📊 [USAGE] Token usage:")
                    logger.info(f"   Input tokens: {usage.get('input_tokens', 0)}")
                    logger.info(f"   Output tokens: {usage.get('output_tokens', 0)}")
                    if "cache_creation_input_tokens" in usage:
                        logger.info(
                            f"   Cache creation tokens: {usage.get('cache_creation_input_tokens', 0)}"
                        )
                    if "cache_read_input_tokens" in usage:
                        logger.info(
                            f"   Cache read tokens: {usage.get('cache_read_input_tokens', 0)}"
                        )

                if "content" in response_json:
                    content = response_json["content"]
                    logger.info(f"   Content blocks: {len(content)}")
                    for i, block in enumerate(content):
                        block_type = block.get("type", "unknown")
                        logger.debug(f"      Block {i}: type={block_type}")
                        if block_type == "text":
                            text_preview = block.get("text", "")[:100]
                            logger.debug(f"         Text preview: {text_preview}...")
                        elif block_type == "tool_use":
                            logger.debug(f"         Tool: {block.get('name', 'N/A')}")

                logger.debug(f"   Full response: {json.dumps(response_json, indent=2)}")
                logger.info(f"📤 [RESPONSE] Returning response to client")
                logger.info("=" * 80)

                try:
                    with open("response.json", "a") as f:
                        json.dump(response_json, f, indent=2)
                        f.write("\n")
                except Exception as e:
                    logger.warning(f"Could not write to response.json: {e}")

                return response_json

    except HTTPException:
        logger.info("=" * 80)
        raise

    except httpx.TimeoutException as e:
        logger.error(f"⏱️ [TIMEOUT] Request to Anthropic API timed out")
        logger.error(f"   Error: {str(e)}")
        logger.info("=" * 80)
        raise HTTPException(
            status_code=504,
            detail={
                "type": "error",
                "error": {
                    "type": "timeout_error",
                    "message": "Request to Anthropic API timed out",
                },
            },
        )

    except httpx.RequestError as e:
        logger.error(f"🌐 [NETWORK ERROR] Network error calling Anthropic API")
        logger.error(f"   Error: {str(e)}")
        logger.info("=" * 80)
        raise HTTPException(
            status_code=502,
            detail={
                "type": "error",
                "error": {"type": "api_error", "message": f"Network error: {str(e)}"},
            },
        )

    except Exception as e:
        logger.error(f"💥 [UNEXPECTED ERROR] Unexpected error in create_message")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Traceback:\n{traceback.format_exc()}")
        logger.info("=" * 80)
        raise HTTPException(
            status_code=500,
            detail={
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": f"Internal server error: {str(e)}",
                },
            },
        )
