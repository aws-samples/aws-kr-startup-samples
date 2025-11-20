from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import logging
import json
from typing import List, Dict, Any, Optional, Union
import traceback
import os
import httpx
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import time
import sys
from dotenv import load_dotenv

from config import (
    BEDROCK_AWS_REGION,
    BEDROCK_FALLBACK_ENABLED,
    RATE_LIMIT_TRACKING_ENABLED,
    RATE_LIMIT_TABLE_NAME,
    RETRY_THRESHOLD_SECONDS,
    MAX_RETRY_WAIT_SECONDS,
    USAGE_TRACKING_ENABLED,
    USAGE_TABLE_NAME,
)
from models import MessagesRequest
from routes.usage import router as usage_router
from routes import messages

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

app.include_router(usage_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


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


# Set up messages router dependencies after all functions are defined
messages.set_dependencies(
    check_rate_limit_status,
    store_rate_limit_status,
    call_bedrock_api,
    mask_api_key,
)
app.include_router(messages.router)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8082")
        sys.exit(0)

    uvicorn.run(app, host="0.0.0.0", port=8082, log_level="info")
