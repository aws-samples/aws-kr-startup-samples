from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import logging
import json
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union, Literal
import traceback
import os
import httpx
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import time

import sys
from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

root_logger = logging.getLogger()
logger = logging.getLogger(__name__)

log_file = os.path.join(os.path.dirname(__file__), "logs", "app.log")
try:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
except:
    log_file = "/tmp/logs/app.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
root_logger.addHandler(console_handler)


app = FastAPI()


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


BEDROCK_AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_FALLBACK_ENABLED = (
    os.getenv("BEDROCK_FALLBACK_ENABLED", "true").lower() == "true"
)

RATE_LIMIT_TRACKING_ENABLED = (
    os.getenv("RATE_LIMIT_TRACKING_ENABLED", "true").lower() == "true"
)
RATE_LIMIT_TABLE_NAME = os.getenv("RATE_LIMIT_TABLE_NAME", "claude-proxy-rate-limits")
RETRY_THRESHOLD_SECONDS = int(os.getenv("RETRY_THRESHOLD_SECONDS", "30"))
MAX_RETRY_WAIT_SECONDS = int(os.getenv("MAX_RETRY_WAIT_SECONDS", "10"))

USAGE_TRACKING_ENABLED = os.getenv("USAGE_TRACKING_ENABLED", "true").lower() == "true"
USAGE_TABLE_NAME = os.getenv("USAGE_TABLE_NAME", "claude-proxy-usage")


def get_bedrock_client():
    try:
        if not BEDROCK_FALLBACK_ENABLED:
            logger.info("🚫 [BEDROCK CONFIG] Bedrock fallback is disabled")
            return None
        return boto3.client("bedrock-runtime", region_name=BEDROCK_AWS_REGION)
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock client: {e}")
        return None


def get_dynamodb_resource():
    try:
        return boto3.resource("dynamodb", region_name=BEDROCK_AWS_REGION)
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB resource: {e}")
        return None


async def check_rate_limit_status(user_id: str) -> tuple[bool, int]:
    if not RATE_LIMIT_TRACKING_ENABLED:
        return False, 0

    try:
        dynamodb = get_dynamodb_resource()
        if not dynamodb:
            return False, 0

        table = dynamodb.Table(RATE_LIMIT_TABLE_NAME)
        response = table.get_item(Key={"user_id": user_id})

        if "Item" not in response:
            return False, 0

        item = response["Item"]
        retry_until = int(item.get("retry_until", 0))
        current_time = int(time.time())

        if retry_until > current_time:
            remaining = retry_until - current_time
            logger.info(
                f"📊 [DDB] User {user_id} is rate limited for {remaining}s more"
            )
            return True, remaining
        else:
            try:
                table.delete_item(Key={"user_id": user_id})
            except:
                pass
            return False, 0

    except Exception as e:
        logger.warning(f"Error checking rate limit status: {e}")
        return False, 0


async def store_rate_limit_status(user_id: str, retry_after_seconds: int):
    if not RATE_LIMIT_TRACKING_ENABLED:
        return

    try:
        dynamodb = get_dynamodb_resource()
        if not dynamodb:
            return

        table = dynamodb.Table(RATE_LIMIT_TABLE_NAME)
        current_time = int(time.time())
        retry_until = current_time + retry_after_seconds
        ttl = retry_until + 3600

        table.put_item(
            Item={
                "user_id": user_id,
                "retry_until": retry_until,
                "retry_after_seconds": retry_after_seconds,
                "ttl": ttl,
                "created_at": current_time,
            }
        )

        logger.info(
            f"📝 [DDB] Stored rate limit for user {user_id}: until {retry_until} ({retry_after_seconds}s)"
        )

    except Exception as e:
        logger.error(f"❌ [DDB] Error storing rate limit: {type(e).__name__}: {e}")


async def store_token_usage(
    user_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    request_type: str,
):
    if not USAGE_TRACKING_ENABLED:
        return

    try:
        dynamodb = get_dynamodb_resource()
        if not dynamodb:
            return

        table = dynamodb.Table(USAGE_TABLE_NAME)
        current_time = int(time.time())
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(current_time))
        ttl = current_time + (90 * 24 * 3600)

        table.put_item(
            Item={
                "user_id": user_id,
                "timestamp": timestamp,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "request_type": request_type,
                "ttl": ttl,
                "created_at": current_time,
            }
        )

        logger.debug(
            f"📊 [USAGE] {user_id}: {input_tokens}+{output_tokens} tokens ({model}, {request_type})"
        )

    except Exception as e:
        logger.warning(f"Error storing token usage: {e}")


def convert_to_bedrock_format(request_data: dict) -> dict:
    messages = request_data.get("messages", [])
    if len(messages) > 0:
        try:
            messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}
        except:
            pass

    bedrock_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": request_data.get("max_tokens", 4096),
        "messages": messages,
    }

    if "system" in request_data:
        bedrock_request["system"] = request_data["system"]
        if len(bedrock_request["system"]) > 0:
            bedrock_request["system"][-1]["cache_control"] = {"type": "ephemeral"}

    if "temperature" in request_data:
        bedrock_request["temperature"] = request_data["temperature"]
    if "top_p" in request_data:
        bedrock_request["top_p"] = request_data["top_p"]
    if "top_k" in request_data:
        bedrock_request["top_k"] = request_data["top_k"]
    if "stop_sequences" in request_data:
        bedrock_request["stop_sequences"] = request_data["stop_sequences"]
    if "tools" in request_data:
        bedrock_request["tools"] = request_data["tools"]
        if len(bedrock_request["tools"]) > 0:
            bedrock_request["tools"][-1]["cache_control"] = {"type": "ephemeral"}

    if "tool_choice" in request_data:
        bedrock_request["tool_choice"] = request_data["tool_choice"]

    return bedrock_request


def convert_from_bedrock_format(bedrock_response: dict, original_model: str) -> dict:
    return {
        "id": bedrock_response.get("id", f"msg_bedrock_{hash(str(bedrock_response))}"),
        "type": "message",
        "role": "assistant",
        "model": original_model,
        "content": bedrock_response.get("content", []),
        "stop_reason": bedrock_response.get("stop_reason", "end_turn"),
        "usage": bedrock_response.get("usage", {}),
    }


async def call_bedrock_api(
    request_data: dict,
    original_model: str,
    stream: bool = False,
    user_id: str = "unknown",
) -> dict:
    try:
        bedrock_client = get_bedrock_client()
        if not bedrock_client:
            raise Exception("Failed to initialize Bedrock client")

        bedrock_model = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
        logger.info(f"🔄 [BEDROCK] {original_model} → {bedrock_model}")

        bedrock_request = convert_to_bedrock_format(request_data)

        if stream:
            logger.info("📡 [BEDROCK] Starting stream")
            response = bedrock_client.invoke_model_with_response_stream(
                modelId=bedrock_model, body=json.dumps(bedrock_request)
            )
            return response
        else:
            logger.info("💬 [BEDROCK] Non-streaming request")
            response = bedrock_client.invoke_model(
                modelId=bedrock_model, body=json.dumps(bedrock_request)
            )

            response_body = json.loads(response["body"].read())
            anthropic_response = convert_from_bedrock_format(
                response_body, original_model
            )

            logger.info(f"✅ [BEDROCK SUCCESS] Received response from Bedrock")
            logger.info(f"   Response ID: {anthropic_response.get('id', 'N/A')}")
            logger.info(
                f"   Stop Reason: {anthropic_response.get('stop_reason', 'N/A')}"
            )

            if "usage" in anthropic_response:
                usage = anthropic_response["usage"]
                logger.info(f"📊 [BEDROCK USAGE] Token usage:")
                logger.info(f"   Input tokens: {usage.get('input_tokens', 0)}")
                logger.info(f"   Output tokens: {usage.get('output_tokens', 0)}")

                await store_token_usage(
                    user_id=user_id,
                    model=original_model,
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    request_type="bedrock",
                )

            return anthropic_response

    except NoCredentialsError:
        logger.error(
            "❌ [BEDROCK ERROR] AWS credentials not found. Please configure AWS credentials."
        )
        raise Exception("AWS credentials not configured for Bedrock fallback")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"❌ [BEDROCK ERROR] AWS Bedrock error: {error_code}")
        logger.error(f"   Error message: {e.response['Error']['Message']}")
        raise Exception(f"Bedrock API error: {error_code}")
    except Exception as e:
        logger.error(f"❌ [BEDROCK ERROR] Unexpected error calling Bedrock: {str(e)}")
        raise


def mask_api_key(api_key: str) -> str:
    if not api_key:
        return "None"
    if len(api_key) <= 12:
        return api_key[:4] + "***"
    return api_key[:10] + "***..." + api_key[-8:]


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error for {request.method} {request.url.path}")
    logger.info(f"Request Headers: {dict(request.headers)}")

    try:
        body = await request.body()
        if body:
            try:
                body_text = body.decode("utf-8")
                logger.error(f"Request Body: {body_text}")
            except UnicodeDecodeError:
                logger.error(f"Request Body (bytes): {body[:200]}...")
    except Exception as e:
        logger.error(f"Could not read request body: {e}")

    logger.error(f"Validation Errors: {exc.errors()}")

    return JSONResponse(
        status_code=422, content={"detail": exc.errors(), "body": exc.body}
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.error(f"ValueError for {request.method} {request.url.path}: {str(exc)}")
    logger.info(f"Request Headers: {dict(request.headers)}")

    try:
        body = await request.body()
        if body:
            try:
                body_text = body.decode("utf-8")
                logger.info(f"Request Body: {body_text}")
            except UnicodeDecodeError:
                logger.info(f"Request Body (bytes): {body[:200]}...")
    except Exception as e:
        logger.error(f"Could not read request body: {e}")

    return JSONResponse(
        status_code=400, content={"error": "Invalid request", "detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled Exception for {request.method} {request.url.path}: {str(exc)}"
    )
    logger.error(f"Exception Type: {type(exc).__name__}")
    logger.info(f"Request Headers: {dict(request.headers)}")
    logger.info(f"Traceback: {traceback.format_exc()}")

    try:
        body = await request.body()
        if body:
            try:
                body_text = body.decode("utf-8")
                logger.info(f"Request Body: {body_text}")
            except UnicodeDecodeError:
                logger.info(f"Request Body (bytes): {body[:200]}...")
    except Exception as e:
        logger.error(f"Could not read request body: {e}")

    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


# Models for Anthropic API requests
class ContentBlockText(BaseModel):
    type: Literal["text"]
    text: str


class ContentBlockThinking(BaseModel):
    type: Literal["thinking"]
    thinking: str
    signature: Optional[str] = None


class ContentBlockImage(BaseModel):
    type: Literal["image"]
    source: Dict[str, Any]


class ContentBlockToolUse(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Any]


class ContentBlockToolResult(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    content: Union[str, List[Dict[str, Any]], Dict[str, Any], List[Any], Any]


class SystemContent(BaseModel):
    type: Literal["text"]
    text: str


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: Union[
        str,
        List[
            Union[
                ContentBlockText,
                ContentBlockImage,
                ContentBlockToolUse,
                ContentBlockToolResult,
                ContentBlockThinking,
            ]
        ],
    ]


class Tool(BaseModel):
    name: str
    description: Optional[str] = None
    input_schema: Dict[str, Any]


class ThinkingConfig(BaseModel):
    type: Literal["enabled"]
    budget_tokens: Optional[int] = None


class MessagesRequest(BaseModel):
    model: str
    max_tokens: int
    messages: List[Message]
    system: Optional[Union[str, List[SystemContent]]] = None
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Dict[str, Any]] = None
    thinking: Optional[ThinkingConfig] = None
    original_model: Optional[str] = None  # Will store the original model name


@app.middleware("http")
async def log_requests(request: Request, call_next):
    method = request.method
    path = request.url.path

    try:
        headers = dict(request.headers)
        logger.debug(f"Request: {method} {path}")
        logger.debug(f"Headers: {headers}")

        if method != "GET":
            try:
                body = await request.body()
                if body:
                    try:
                        body_text = body.decode("utf-8")
                        try:
                            body_json = json.loads(body_text)
                            logger.debug(
                                f"Request Body (JSON): {json.dumps(body_json, indent=2)}"
                            )
                        except json.JSONDecodeError:
                            body_preview = (
                                body_text[:500] + "..."
                                if len(body_text) > 500
                                else body_text
                            )
                            logger.debug(f"Request Body (Text): {body_preview}")
                    except UnicodeDecodeError:
                        body_preview = (
                            str(body[:100]) + "..." if len(body) > 100 else str(body)
                        )
                        logger.debug(f"Request Body (Bytes): {body_preview}")

                    request._body = body
            except Exception as e:
                logger.warning(f"Error reading request body: {e}")

        response = await call_next(request)
        logger.debug(f"Response Status: {response.status_code}")

    except Exception as e:
        logger.error(f"Error in request middleware: {e}")
        response = await call_next(request)

    return response


@app.post("/v1/messages")
@app.post("/user/{user_id}/v1/messages")
async def create_message(
    request: MessagesRequest, raw_request: Request, user_id: str = "default"
):
    """
    Anthropic Messages API 프록시 엔드포인트

    클라이언트 요청을 Anthropic API / Amazon Bedrock으로 전달하고 응답을 pass-through합니다.

    Routes:
    - /v1/messages (user_id = "default")
    - /user/{user_id}/v1/messages (user_id from path)
    """

    # 요청 시작 로깅
    logger.info("=" * 80)
    logger.info(f"📥 [REQUEST] New /v1/messages request received from user: {user_id}")

    # 모든 헤더 로깅 (x-api-key는 마스킹)
    logger.info("📋 [HEADERS] Request headers:")
    for header_name, header_value in raw_request.headers.items():
        if header_name.lower() in ["x-api-key", "authorization"]:
            # API 키 관련 헤더는 마스킹
            logger.info(f"   {header_name}: {mask_api_key(header_value)}")
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
        # 1. API 키 처리
        # 우선순위: x-api-key 헤더 > Authorization Bearer 헤더 > 환경변수 (fallback)

        # x-api-key 헤더 체크
        header_api_key = raw_request.headers.get("x-api-key")

        # Authorization Bearer 헤더 체크 (Claude Code subscription 방식)
        auth_header = raw_request.headers.get(
            "authorization"
        ) or raw_request.headers.get("Authorization")
        bearer_token = None
        if auth_header and auth_header.startswith("Bearer "):
            bearer_token = auth_header.replace("Bearer ", "").strip()

        # 환경변수 체크
        env_api_key = os.getenv("ANTHROPIC_API_KEY")
        env_auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")

        # 우선순위에 따라 API 키 선택 및 인증 방식 결정
        use_bearer_auth = False  # Authorization Bearer 헤더 사용 여부

        if header_api_key:
            api_key = header_api_key
            auth_source = f"x-api-key header: {mask_api_key(header_api_key)}"
            use_bearer_auth = False
        elif bearer_token:
            api_key = bearer_token
            auth_source = f"Authorization Bearer header (Claude Code subscription): {mask_api_key(bearer_token)}"
            use_bearer_auth = True
        elif env_api_key:
            api_key = env_api_key
            auth_source = (
                f"ANTHROPIC_API_KEY environment variable: {mask_api_key(env_api_key)}"
            )
            use_bearer_auth = False
        elif env_auth_token:
            api_key = env_auth_token
            auth_source = f"ANTHROPIC_AUTH_TOKEN environment variable (Claude Code): {mask_api_key(env_auth_token)}"
            use_bearer_auth = True  # Claude Code 방식이므로 Bearer 사용
        else:
            api_key = None
            auth_source = "None"

        # API 키 출처 로깅
        logger.info(f"🔑 [AUTH] Using API key from {auth_source}")

        # Prepare request data early for potential Bedrock fallback
        request_data = request.model_dump(exclude_none=True, exclude={"original_model"})

        # thinking 필드를 dict로 변환 (ThinkingConfig -> dict)
        if request.thinking is not None:
            request_data["thinking"] = request.thinking.model_dump(exclude_none=True)

        if RATE_LIMIT_TRACKING_ENABLED:
            is_rate_limited, remaining_seconds = await check_rate_limit_status(user_id)
            if is_rate_limited:
                logger.info(
                    f"⏳ [RATE LIMIT CHECK] User {user_id} is rate limited for {remaining_seconds}s"
                )

                if BEDROCK_FALLBACK_ENABLED:
                    logger.info("🔄 [FALLBACK] Using Bedrock (stored rate limit)")
                    try:
                        bedrock_response = await call_bedrock_api(
                            request_data,
                            request.model,
                            stream=request.stream,
                            user_id=user_id,
                        )

                        if request.stream:
                            return bedrock_response  # Already a StreamingResponse
                        else:
                            logger.info(
                                "✅ [BEDROCK FALLBACK] Successfully received response from Bedrock (via stored rate limit)"
                            )
                            logger.info(
                                "📤 [RESPONSE] Returning Bedrock response to client"
                            )
                            logger.info("=" * 80)

                            # Save to response.json
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
                        # Continue to try Anthropic API anyway
                else:
                    logger.warning(
                        "⚠️ [RATE LIMIT] User is rate limited but Bedrock fallback is disabled"
                    )
            else:
                logger.debug(
                    f"✅ [RATE LIMIT CHECK] User {user_id} is not currently rate limited"
                )

        # Log Bedrock fallback status
        if BEDROCK_FALLBACK_ENABLED:
            try:
                bedrock_client = get_bedrock_client()
                if bedrock_client:
                    logger.info(
                        f"🛡️ [BEDROCK CONFIG] Bedrock fallback is enabled (region: {BEDROCK_AWS_REGION})"
                    )
                else:
                    logger.warning(
                        f"⚠️ [BEDROCK CONFIG] Bedrock fallback enabled but client initialization failed"
                    )
            except Exception as e:
                logger.warning(
                    f"⚠️ [BEDROCK CONFIG] Bedrock fallback enabled but client check failed: {e}"
                )
        else:
            logger.info(f"🚫 [BEDROCK CONFIG] Bedrock fallback is disabled")

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

        # 2. API Base URL 설정
        api_base = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com")
        api_url = f"{api_base}/v1/messages"

        # 3. Anthropic API 요청 헤더 준비
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # 인증 방식에 따라 적절한 헤더 설정
        if use_bearer_auth:
            # Authorization Bearer 헤더 사용 (Claude Code 방식)
            headers["Authorization"] = f"Bearer {api_key}"
            logger.info(f"   Using Authorization Bearer header for authentication")
        else:
            # x-api-key 헤더 사용 (표준 Anthropic 방식)
            headers["x-api-key"] = api_key
            logger.info(f"   Using x-api-key header for authentication")

        # anthropic-beta 헤더 전달 (있는 경우)
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
                logger.info(f"   {header_name}: {mask_api_key(header_value)}")
            else:
                logger.info(f"   {header_name}: {header_value}")
        logger.debug(f"   Full request data: {json.dumps(request_data, indent=2)}")

        # 4. Anthropic API 호출
        async with httpx.AsyncClient(timeout=600.0) as client:
            # ########## Force 429 Rate Limit Test ##########
            if os.getenv("FORCE_RATE_LIMIT", "false").lower() == "true":
                logger.warning("🧪 [TEST MODE] Simulating 429 rate limit error")

                retry_after_seconds = 60
                logger.info(
                    f"⏱️ [RATE LIMIT] retry-after: {retry_after_seconds} seconds for user {user_id}"
                )

                # Store rate limit in DynamoDB
                await store_rate_limit_status(user_id, retry_after_seconds)

                if BEDROCK_FALLBACK_ENABLED:
                    logger.info(
                        "🔄 [FALLBACK] Simulated 429, attempting Bedrock fallback"
                    )
                    try:
                        bedrock_response = await call_bedrock_api(
                            request_data,
                            request.model,
                            stream=request.stream,
                            user_id=user_id,
                        )

                        if request.stream:
                            # Bedrock streaming response handler
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
            # ####### End of Force 429 Test #######

            # 스트리밍 요청인 경우
            if request.stream:
                logger.info("📡 [STREAM] Streaming request detected")

                # 스트리밍 요청 - context manager를 사용하지 않고 직접 관리
                streaming_response = await client.send(
                    client.build_request(
                        "POST", api_url, headers=headers, json=request_data
                    ),
                    stream=True,
                )

                # 에러 체크
                if streaming_response.status_code != 200:
                    error_text = await streaming_response.aread()
                    logger.error(
                        f"❌ [ERROR] Anthropic API error: {streaming_response.status_code}"
                    )
                    logger.error(f"📋 [ERROR HEADERS] Response headers from Anthropic:")
                    for header_name, header_value in streaming_response.headers.items():
                        logger.error(f"   {header_name}: {header_value}")
                    logger.error(f"   Error body: {error_text.decode()}")

                    # Check if this is a 429 rate limit error and fallback to Bedrock
                    if streaming_response.status_code == 429:
                        # Parse retry-after header
                        retry_after = streaming_response.headers.get("retry-after")
                        retry_after_seconds = int(retry_after) if retry_after else 0

                        logger.info(
                            f"⏱️ [RATE LIMIT] retry-after: {retry_after_seconds} seconds for user {user_id}"
                        )

                        # Store rate limit info in DynamoDB for future requests
                        if retry_after_seconds > 0:
                            await store_rate_limit_status(user_id, retry_after_seconds)

                        if BEDROCK_FALLBACK_ENABLED:
                            logger.info(
                                "🔄 [FALLBACK] Detected 429 rate limit error, attempting Bedrock fallback for streaming request"
                            )
                            try:
                                # For streaming, we need to handle Bedrock streaming differently
                                bedrock_response = await call_bedrock_api(
                                    request_data,
                                    request.model,
                                    stream=True,
                                    user_id=user_id,
                                )

                                # Handle Bedrock streaming response
                                async def bedrock_stream_generator():
                                    try:
                                        for event in bedrock_response["body"]:
                                            chunk = event.get("chunk", {})
                                            if chunk:
                                                chunk_bytes = chunk.get("bytes", b"")
                                                if chunk_bytes:
                                                    # Parse the chunk and convert to Anthropic SSE format
                                                    chunk_data = json.loads(
                                                        chunk_bytes.decode()
                                                    )
                                                    if (
                                                        chunk_data.get("type")
                                                        == "content_block_delta"
                                                    ):
                                                        # Convert to Anthropic SSE format
                                                        sse_data = f"data: {json.dumps(chunk_data)}\n\n"
                                                        yield sse_data.encode()
                                                    elif (
                                                        chunk_data.get("type")
                                                        == "message_stop"
                                                    ):
                                                        # Send final event
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
                                # If Bedrock also fails, return original Anthropic error

                    # If not 429 or Bedrock fallback failed, return original error
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

                # SSE 스트리밍 응답 전달
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
                        # 스트림 정리
                        await streaming_response.aclose()
                        logger.debug("   Stream closed")

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )

            # 비스트리밍 요청인 경우
            else:
                logger.info("💬 [NON-STREAM] Non-streaming request")

                response = await client.post(
                    api_url, headers=headers, json=request_data
                )

                # 에러 체크
                if response.status_code != 200:
                    logger.error(
                        f"❌ [ERROR] Anthropic API error: {response.status_code}"
                    )
                    logger.error(f"📋 [ERROR HEADERS] Response headers from Anthropic:")
                    for header_name, header_value in response.headers.items():
                        logger.error(f"   {header_name}: {header_value}")
                    logger.error(f"   Error body: {response.text}")

                    # Check if this is a 429 rate limit error and fallback to Bedrock
                    if response.status_code == 429:
                        # Parse retry-after header
                        retry_after = response.headers.get("retry-after")
                        retry_after_seconds = int(retry_after) if retry_after else 0

                        logger.info(
                            f"⏱️ [RATE LIMIT] retry-after: {retry_after_seconds} seconds for user {user_id}"
                        )

                        # Store rate limit info in DynamoDB for future requests
                        if retry_after_seconds > 0:
                            await store_rate_limit_status(user_id, retry_after_seconds)

                        if BEDROCK_FALLBACK_ENABLED:
                            logger.info(
                                "🔄 [FALLBACK] Detected 429 rate limit error, attempting Bedrock fallback"
                            )
                            try:
                                # Attempt Bedrock fallback
                                bedrock_response = await call_bedrock_api(
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

                                # Save to response.json file (existing behavior)
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
                                # If Bedrock also fails, return original Anthropic error

                    # If not 429 or Bedrock fallback failed, return original error
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

                # 성공 응답
                response_json = response.json()

                # 응답 상세 정보 로깅
                logger.info(f"✅ [SUCCESS] Received response from Anthropic API")
                logger.info(f"   Status: {response.status_code}")
                logger.info(f"   Response ID: {response_json.get('id', 'N/A')}")
                logger.info(f"   Model: {response_json.get('model', 'N/A')}")
                logger.info(
                    f"   Stop Reason: {response_json.get('stop_reason', 'N/A')}"
                )

                # Usage 정보 로깅
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

                # Content 타입 로깅
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

                # response.json 파일에 로깅 (기존 동작 유지)
                try:
                    with open("response.json", "a") as f:
                        json.dump(response_json, f, indent=2)
                        f.write("\n")
                except Exception as e:
                    logger.warning(f"Could not write to response.json: {e}")

                return response_json

    except HTTPException:
        # HTTPException은 그대로 re-raise
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


@app.get("/v1/usage/me")
async def get_my_usage(
    raw_request: Request,
    days: int = None,
    date: str = None,
    request_type: str = None,
):
    """
    현재 유저의 토큰 사용량 조회 (쿼리 파라미터에서 user_id 자동 추출)

    Args:
        days: 조회 기간 (일 단위) - date와 함께 사용 불가
        date: 특정 날짜 조회 (YYYY-MM-DD 형식) - days와 함께 사용 불가
        request_type: "anthropic", "bedrock", 또는 None (전체)

    Returns:
        현재 유저의 토큰 사용량 통계

    Example:
        GET /v1/usage/me?days=7&request_type=bedrock  # 최근 7일
        GET /v1/usage/me?date=2025-11-14&request_type=bedrock  # 특정 날짜 하루
    """
    user_id = raw_request.query_params.get("claude-code-user", "default")
    return await get_user_usage(
        user_id=user_id, days=days, date=date, request_type=request_type
    )


async def get_user_usage(
    user_id: str,
    days: int = None,
    date: str = None,
    request_type: str = None,
):
    """
    특정 유저의 토큰 사용량 조회

    Args:
        user_id: 유저 식별자
        days: 조회 기간 (일 단위) - date와 함께 사용 불가
        date: 특정 날짜 (YYYY-MM-DD 형식) - days와 함께 사용 불가
        request_type: "anthropic", "bedrock", 또는 None (전체)

    Returns:
        유저의 토큰 사용량 통계 (총합, 일별 통계 등)
    """
    try:
        from datetime import datetime, timedelta
        from boto3.dynamodb.conditions import Key

        dynamodb = get_dynamodb_resource()
        if not dynamodb:
            return {"error": "DynamoDB not available"}

        table = dynamodb.Table(USAGE_TABLE_NAME)

        # date와 days 둘 다 없으면 기본값 7일
        if date is None and days is None:
            days = 7

        # 날짜 범위 계산 (UTC 기준)
        if date:
            # 특정 날짜 하루만 조회
            start_date = date  # YYYY-MM-DD
            end_date = date
        else:
            # days 기간 조회
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = datetime.utcnow().strftime("%Y-%m-%d")

        # DynamoDB 쿼리 실행
        if date:
            # 특정 날짜 하루만 조회 (YYYY-MM-DD로 시작하는 모든 timestamp)
            response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id)
                & Key("timestamp").between(start_date, start_date + "T99:99:99")
            )
        else:
            # days 기간 조회
            response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id)
                & Key("timestamp").gte(start_date)
            )

        items = response.get("Items", [])

        # request_type 필터링 (선택적)
        if request_type:
            items = [item for item in items if item.get("request_type") == request_type]

        # 전체 통계 계산
        total_input = sum(item.get("input_tokens", 0) for item in items)
        total_output = sum(item.get("output_tokens", 0) for item in items)
        total_requests = len(items)

        # 일별 통계 계산
        daily_stats = {}
        for item in items:
            day = item["timestamp"][:10]  # YYYY-MM-DD 추출
            if day not in daily_stats:
                daily_stats[day] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "requests": 0,
                }
            daily_stats[day]["input_tokens"] += item.get("input_tokens", 0)
            daily_stats[day]["output_tokens"] += item.get("output_tokens", 0)
            daily_stats[day]["requests"] += 1

        # 응답 구성
        result = {
            "user_id": user_id,
            "request_type": request_type or "all",
            "summary": {
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "total_requests": total_requests,
            },
            "daily_stats": daily_stats,
        }

        # date 또는 days 정보 추가
        if date:
            result["date"] = date
        else:
            result["period_days"] = days

        return result

    except Exception as e:
        logger.error(f"Error fetching usage for user {user_id}: {e}")
        return {"error": str(e)}


@app.get("/v1/usage")
async def get_all_users_usage(
    days: int = None,
    date: str = None,
    request_type: str = "bedrock",
):
    """
    전체 유저의 토큰 사용량 조회 (관리자용)

    Args:
        days: 조회 기간 (일 단위) - date와 함께 사용 불가
        date: 특정 날짜 (YYYY-MM-DD 형식) - days와 함께 사용 불가
        request_type: "anthropic", "bedrock", 또는 "all" (기본 bedrock)

    Returns:
        전체 유저의 토큰 사용량 통계

    Example:
        GET /v1/usage?days=7&request_type=bedrock  # 최근 7일
        GET /v1/usage?date=2025-11-14&request_type=bedrock  # 특정 날짜
    """
    try:
        from datetime import datetime, timedelta
        from boto3.dynamodb.conditions import Attr

        dynamodb = get_dynamodb_resource()
        if not dynamodb:
            return {"error": "DynamoDB not available"}

        table = dynamodb.Table(USAGE_TABLE_NAME)

        # date와 days 둘 다 없으면 기본값 7일
        if date is None and days is None:
            days = 7

        # 시작/종료 날짜 계산
        if date:
            # 특정 날짜 하루만
            start_timestamp = date
            end_timestamp = date + "T99:99:99"
        else:
            # days 기간
            start_timestamp = (datetime.utcnow() - timedelta(days=days)).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
            end_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

        # Scan으로 데이터 조회 (FilterExpression 사용)
        if date:
            # 특정 날짜 필터링
            if request_type == "all":
                response = table.scan(
                    FilterExpression=Attr("timestamp").between(
                        start_timestamp, end_timestamp
                    )
                )
            else:
                response = table.scan(
                    FilterExpression=Attr("timestamp").between(
                        start_timestamp, end_timestamp
                    )
                    & Attr("request_type").eq(request_type)
                )
        else:
            # days 기간 필터링
            if request_type == "all":
                response = table.scan(
                    FilterExpression=Attr("timestamp").gte(start_timestamp)
                )
            else:
                response = table.scan(
                    FilterExpression=Attr("timestamp").gte(start_timestamp)
                    & Attr("request_type").eq(request_type)
                )

        items = response.get("Items", [])

        # 유저별 통계 집계
        user_stats = {}
        for item in items:
            uid = item.get("user_id")
            if uid not in user_stats:
                user_stats[uid] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "requests": 0,
                }
            user_stats[uid]["input_tokens"] += item.get("input_tokens", 0)
            user_stats[uid]["output_tokens"] += item.get("output_tokens", 0)
            user_stats[uid]["requests"] += 1

        # 총합 계산
        total_users = len(user_stats)
        total_input = sum(s["input_tokens"] for s in user_stats.values())
        total_output = sum(s["output_tokens"] for s in user_stats.values())
        total_requests = sum(s["requests"] for s in user_stats.values())

        # 응답 구성
        result = {
            "request_type": request_type,
            "summary": {
                "total_users": total_users,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "total_requests": total_requests,
            },
            "users": user_stats,
        }

        # date 또는 days 정보 추가
        if date:
            result["date"] = date
        else:
            result["period_days"] = days

        return result

    except Exception as e:
        logger.error(f"Error fetching all users usage: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8082")
        sys.exit(0)

    # Configure uvicorn to run with minimal logs
    uvicorn.run(app, host="0.0.0.0", port=8082, log_level="info")
