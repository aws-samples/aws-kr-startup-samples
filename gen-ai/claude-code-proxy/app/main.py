from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn
import logging
import json
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any, Optional, Union, Literal
import traceback

import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO level to show more details
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Apply the filter to the root logger to catch all messages
root_logger = logging.getLogger()
logger = logging.getLogger(__name__)


app = FastAPI()


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
    enabled: bool = True


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
        with open("response.json", "a") as f:
            json.dump(response.json(), f)

    except Exception as e:
        logger.error(f"Error in request middleware: {e}")
        response = await call_next(request)

    return response


@app.post("/v1/messages")
async def create_message(request: MessagesRequest, raw_request: Request):
    # print the body here
    body = await raw_request.body()

    # Parse the raw body as JSON since it's bytes
    body_json = json.loads(body.decode("utf-8"))

    logger.debug(f"{request}\n{body_json}")


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
