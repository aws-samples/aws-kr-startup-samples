from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .logging import get_logger, setup_logging
from .api import (
    proxy_router,
    admin_auth_router,
    admin_users_router,
    admin_keys_router,
    admin_usage_router,
    admin_pricing_router,
)

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Claude Code Proxy",
    description="Proxy between Claude Code and Amazon Bedrock with automatic failover",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proxy_router)
app.include_router(admin_auth_router)
app.include_router(admin_users_router)
app.include_router(admin_keys_router)
app.include_router(admin_usage_router)
app.include_router(admin_pricing_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.info(
        "request_validation_error",
        method=request.method,
        path=request.url.path,
        errors=exc.errors(),
    )
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(HTTPException)
async def http_exception_logger(request: Request, exc: HTTPException):
    if exc.status_code == 400:
        logger.info(
            "http_exception",
            method=request.method,
            path=request.url.path,
            status_code=exc.status_code,
            detail=str(exc.detail),
        )
    return await http_exception_handler(request, exc)
