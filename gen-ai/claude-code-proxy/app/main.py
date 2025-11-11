from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import logging
import json
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any, Optional, Union, Literal
import traceback
import os
import httpx

import boto3

import sys

# Configure logging with both console and file handlers
logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO level to show more details
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Apply the filter to the root logger to catch all messages
root_logger = logging.getLogger()
logger = logging.getLogger(__name__)

# Add file handler to save logs to a file
log_file = os.path.join(os.path.dirname(__file__), "logs", "app.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
root_logger.addHandler(file_handler)

# Also add console handler explicitly for completeness
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)


app = FastAPI()


# Helper function to mask API key for logging
def mask_api_key(api_key: str) -> str:
    """API 키를 마스킹하여 로깅용으로 반환 (예: sk-ant-***...xyz)"""
    if not api_key:
        return "None"
    if len(api_key) <= 12:
        return api_key[:4] + "***"
    return api_key[:10] + "***..." + api_key[-8:]


# Exception handlers for capturing invalid requests
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log the validation error with request details
    logger.error(f"Validation Error for {request.method} {request.url.path}")
    logger.error(f"Request Headers: {dict(request.headers)}")

    # Try to log the request body
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
    logger.error(f"Request Headers: {dict(request.headers)}")

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

    return JSONResponse(
        status_code=400, content={"error": "Invalid request", "detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled Exception for {request.method} {request.url.path}: {str(exc)}"
    )
    logger.error(f"Exception Type: {type(exc).__name__}")
    logger.error(f"Request Headers: {dict(request.headers)}")
    logger.error(f"Traceback: {traceback.format_exc()}")

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

    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


# Models for Anthropic API requests
class ContentBlockText(BaseModel):
    type: Literal["text"]
    text: str


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
    # Get request details
    method = request.method
    path = request.url.path

    # Log request headers and body for debugging invalid requests
    try:
        # Get request headers
        headers = dict(request.headers)
        logger.debug(f"Request: {method} {path}")
        logger.debug(f"Headers: {headers}")

        # For non-GET requests, try to log the body
        if method != "GET":
            try:
                # Read the request body
                body = await request.body()
                if body:
                    # Try to decode as UTF-8 and parse as JSON
                    try:
                        body_text = body.decode("utf-8")
                        # Try to parse as JSON for better formatting
                        try:
                            body_json = json.loads(body_text)
                            logger.debug(
                                f"Request Body (JSON): {json.dumps(body_json, indent=2)}"
                            )
                        except json.JSONDecodeError:
                            # If not valid JSON, log as text (truncate if too long)
                            body_preview = (
                                body_text[:500] + "..."
                                if len(body_text) > 500
                                else body_text
                            )
                            logger.debug(f"Request Body (Text): {body_preview}")
                    except UnicodeDecodeError:
                        # If can't decode as UTF-8, log as bytes (truncated)
                        body_preview = (
                            str(body[:100]) + "..." if len(body) > 100 else str(body)
                        )
                        logger.debug(f"Request Body (Bytes): {body_preview}")

                    # Store body for downstream processing
                    request._body = body
            except Exception as e:
                logger.warning(f"Error reading request body: {e}")

        # Process the request and get the response
        response = await call_next(request)

        # Log response status
        logger.debug(f"Response Status: {response.status_code}")

    except Exception as e:
        logger.error(f"Error in request middleware: {e}")
        response = await call_next(request)

    return response

def invoke_bedrock(body, headers):

    logger.info(f"=====INVOKE BEDROCK=====")
    
    model = "global.anthropic.claude-haiku-4-5-20251001-v1:0" # body["model"]
    messages = body["messages"]
    max_tokens = body["max_tokens"]
    temperature = body["temperature"]
    tools = body["tools"]


    # anthropic_version = headers["anthropic_version"]
    anthropic_beta = list(headers["anthropic-beta"].split(","))

    client = boto3.client('bedrock-runtime', region_name='us-west-2')

    request_data = {
        "anthropic_version": "bedrock-2023-05-31",
        "anthropic_beta": anthropic_beta,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
        "tools": tools
    }
    
    res = client.invoke_model(
        modelId = model,
        body=json.dumps(request_data)
    )

    model_response = json.loads(res["body"].read())

    logger.info(f"{model_response}")
    
    return model_response

async def invoke_bedrock_stream(body):
    
    logger.info(f"=====INVOKE BEDROCK STREAM=====")
    
    model = "global.anthropic.claude-haiku-4-5-20251001-v1:0" # body["model"]
    messages = body["messages"]
    max_tokens = body["max_tokens"]
    temperature = body["temperature"]
    tools = body["tools"]


    client = boto3.client('bedrock-runtime', region_name='us-west-2')

    request_data = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
        "tools": tools,
    }
    
    res = client.invoke_model_with_response_stream(
        modelId = model,
        body=json.dumps(request_data)
    )

    for event in res["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        if chunk["type"] == "content_block_delta":
            yield chunk["delta"].get("text", "")


@app.post("/v1/messages")
async def create_message(request: MessagesRequest, raw_request: Request):
    """
    Anthropic Messages API 프록시 엔드포인트
    
    클라이언트 요청을 Anthropic API / Amazon Bedrock으로 전달하고 응답을 pass-through합니다.
    """
    # 요청 시작 로깅
    logger.info("="*80)
    logger.info("📥 [REQUEST] New /v1/messages request received")
    
    # 모든 헤더 로깅 (x-api-key는 마스킹)
    logger.info("📋 [HEADERS] Request headers:")
    for header_name, header_value in raw_request.headers.items():
        if header_name.lower() in ['x-api-key', 'authorization']:
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
        logger.info(f"   System Prompt: {'Yes (string)' if isinstance(request.system, str) else f'Yes ({len(request.system)} parts)'}")
    if request.tools:
        logger.info(f"   Tools: {len(request.tools)} tools provided")
    if request.thinking:
        logger.info(f"   Thinking: Enabled")
    
    try:
        # 1. API 키 처리
        # 우선순위: x-api-key 헤더 > Authorization Bearer 헤더 > ANTHROPIC_API_KEY 환경변수 > ANTHROPIC_AUTH_TOKEN 환경변수
        
        # x-api-key 헤더 체크
        header_api_key = raw_request.headers.get("x-api-key")
        
        # Authorization Bearer 헤더 체크 (Claude Code subscription 방식)
        auth_header = raw_request.headers.get("authorization") or raw_request.headers.get("Authorization")
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
            auth_source = f"ANTHROPIC_API_KEY environment variable: {mask_api_key(env_api_key)}"
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
        
        if not api_key:
            logger.error("❌ [AUTH] Missing API key - Please provide one of:")
            logger.error("   - x-api-key header")
            logger.error("   - Authorization: Bearer <token> header (Claude Code)")
            logger.error("   - ANTHROPIC_API_KEY environment variable")
            logger.error("   - ANTHROPIC_AUTH_TOKEN environment variable (Claude Code)")
            raise HTTPException(
                status_code=401,
                detail={
                    "type": "error",
                    "error": {
                        "type": "authentication_error",
                        "message": "Missing API key. Please provide x-api-key header, Authorization Bearer header, or set ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN environment variable."
                    }
                }
            )
        
        # 2. API Base URL 설정
        api_base = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com")
        api_url = f"{api_base}/v1/messages"
        
        # 3. 요청 데이터 준비 (Anthropic 형식 유지)
        request_data = request.model_dump(exclude_none=True, exclude={"original_model"})
        
        # thinking 필드를 dict로 변환 (ThinkingConfig -> dict)
        if request.thinking is not None:
            request_data["thinking"] = request.thinking.model_dump(exclude_none=True)
        
        # 4. Anthropic API 요청 헤더 준비
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
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
            logger.info(f"   anthropic-beta header: {raw_request.headers['anthropic-beta']}")
        
        logger.info(f"🚀 [FORWARD] Forwarding request to Anthropic API")
        logger.info(f"   Target URL: {api_url}")
        logger.info(f"📋 [FORWARD HEADERS] Headers being sent to Anthropic:")
        for header_name, header_value in headers.items():
            if header_name.lower() in ['x-api-key', 'authorization']:
                logger.info(f"   {header_name}: {mask_api_key(header_value)}")
            else:
                logger.info(f"   {header_name}: {header_value}")
        logger.debug(f"   Full request data: {json.dumps(request_data, indent=2)}")


        # 5-0. Bedrock API 호출
        if request.stream:
            return StreamingResponse(
                invoke_bedrock_stream(request_data), 
                media_type="text/event-stream",
                headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive"
                    }
                )

        else:
            response_bedrock = invoke_bedrock(request_data, headers)
            return response_bedrock
        
        # 5. Anthropic API 호출
        async with httpx.AsyncClient(timeout=600.0) as client:
            # 스트리밍 요청인 경우
            if request.stream:
                logger.info("📡 [STREAM] Streaming request detected")
                
                # 스트리밍 요청 - context manager를 사용하지 않고 직접 관리
                streaming_response = await client.send(
                    client.build_request(
                        "POST",
                        api_url,
                        headers=headers,
                        json=request_data
                    ),
                    stream=True
                )
                
                # 에러 체크
                if streaming_response.status_code != 200:
                    error_text = await streaming_response.aread()
                    logger.error(f"❌ [ERROR] Anthropic API error: {streaming_response.status_code}")
                    logger.error(f"📋 [ERROR HEADERS] Response headers from Anthropic:")
                    for header_name, header_value in streaming_response.headers.items():
                        logger.error(f"   {header_name}: {header_value}")
                    logger.error(f"   Error body: {error_text.decode()}")
                    try:
                        error_json = json.loads(error_text)
                        raise HTTPException(status_code=streaming_response.status_code, detail=error_json)
                    except json.JSONDecodeError:
                        raise HTTPException(
                            status_code=streaming_response.status_code,
                            detail={"error": error_text.decode()}
                        )
                
                logger.info(f"✅ [STREAM] Successfully connected to Anthropic API streaming endpoint")
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
                                logger.debug(f"   First chunk received (size: {len(chunk)} bytes)")
                            yield chunk
                        logger.info(f"✅ [STREAM] Streaming completed - {chunk_count} chunks sent")
                    except Exception as e:
                        logger.error(f"❌ [STREAM] Error streaming response: {e}")
                        raise
                    finally:
                        # 스트림 정리
                        await streaming_response.aclose()
                        logger.debug("   Stream closed")
                
                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive"
                    }
                )
            
            # 비스트리밍 요청인 경우
            else:
                logger.info("💬 [NON-STREAM] Non-streaming request")
                
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=request_data
                )
                
                # 에러 체크
                if response.status_code != 200:
                    logger.error(f"❌ [ERROR] Anthropic API error: {response.status_code}")
                    logger.error(f"📋 [ERROR HEADERS] Response headers from Anthropic:")
                    for header_name, header_value in response.headers.items():
                        logger.error(f"   {header_name}: {header_value}")
                    logger.error(f"   Error body: {response.text}")
                    try:
                        error_json = response.json()
                        raise HTTPException(status_code=response.status_code, detail=error_json)
                    except json.JSONDecodeError:
                        raise HTTPException(
                            status_code=response.status_code,
                            detail={"error": response.text}
                        )
                
                # 성공 응답
                response_json = response.json()
                
                # 응답 상세 정보 로깅
                logger.info(f"✅ [SUCCESS] Received response from Anthropic API")
                logger.info(f"   Status: {response.status_code}")
                logger.info(f"   Response ID: {response_json.get('id', 'N/A')}")
                logger.info(f"   Model: {response_json.get('model', 'N/A')}")
                logger.info(f"   Stop Reason: {response_json.get('stop_reason', 'N/A')}")
                
                # Usage 정보 로깅
                if 'usage' in response_json:
                    usage = response_json['usage']
                    logger.info(f"📊 [USAGE] Token usage:")
                    logger.info(f"   Input tokens: {usage.get('input_tokens', 0)}")
                    logger.info(f"   Output tokens: {usage.get('output_tokens', 0)}")
                    if 'cache_creation_input_tokens' in usage:
                        logger.info(f"   Cache creation tokens: {usage.get('cache_creation_input_tokens', 0)}")
                    if 'cache_read_input_tokens' in usage:
                        logger.info(f"   Cache read tokens: {usage.get('cache_read_input_tokens', 0)}")
                
                # Content 타입 로깅
                if 'content' in response_json:
                    content = response_json['content']
                    logger.info(f"   Content blocks: {len(content)}")
                    for i, block in enumerate(content):
                        block_type = block.get('type', 'unknown')
                        logger.debug(f"      Block {i}: type={block_type}")
                        if block_type == 'text':
                            text_preview = block.get('text', '')[:100]
                            logger.debug(f"         Text preview: {text_preview}...")
                        elif block_type == 'tool_use':
                            logger.debug(f"         Tool: {block.get('name', 'N/A')}")
                
                logger.debug(f"   Full response: {json.dumps(response_json, indent=2)}")
                logger.info(f"📤 [RESPONSE] Returning response to client")
                logger.info("="*80)
                
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
        logger.info("="*80)
        raise
    
    except httpx.TimeoutException as e:
        logger.error(f"⏱️ [TIMEOUT] Request to Anthropic API timed out")
        logger.error(f"   Error: {str(e)}")
        logger.info("="*80)
        raise HTTPException(
            status_code=504,
            detail={
                "type": "error",
                "error": {
                    "type": "timeout_error",
                    "message": "Request to Anthropic API timed out"
                }
            }
        )
    
    except httpx.RequestError as e:
        logger.error(f"🌐 [NETWORK ERROR] Network error calling Anthropic API")
        logger.error(f"   Error: {str(e)}")
        logger.info("="*80)
        raise HTTPException(
            status_code=502,
            detail={
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": f"Network error: {str(e)}"
                }
            }
        )
    
    except Exception as e:
        logger.error(f"💥 [UNEXPECTED ERROR] Unexpected error in create_message")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Traceback:\n{traceback.format_exc()}")
        logger.info("="*80)
        raise HTTPException(
            status_code=500,
            detail={
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": f"Internal server error: {str(e)}"
                }
            }
        )


# @app.get("/")
# async def root():
#     return {"message": "Anthropic Proxy"}

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8082")
        sys.exit(0)

    # Configure uvicorn to run with minimal logs
    uvicorn.run(app, host="0.0.0.0", port=8082, log_level="info")
