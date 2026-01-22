from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    admin_auth_router,
    admin_keys_router,
    admin_models_router,
    admin_pricing_router,
    admin_usage_router,
    admin_users_router,
    proxy_router,
)
from .db.session import async_session_factory
from .logging import setup_logging
from .proxy import get_proxy_deps
from .proxy.model_mapping import build_default_bedrock_model_resolver, set_cached_db_mappings
from .repositories import ModelMappingRepository

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load DB model mappings on startup."""
    try:
        async with async_session_factory() as session:
            repo = ModelMappingRepository(session)
            db_mappings = await repo.get_active_mappings_dict()
            set_cached_db_mappings(db_mappings)

            # Update the global resolver with DB mappings
            deps = get_proxy_deps()
            deps.bedrock_model_resolver = build_default_bedrock_model_resolver(db_mappings)
    except Exception:
        # Continue startup even if DB load fails (will use defaults)
        pass

    yield


app = FastAPI(
    title="Claude Code Proxy",
    description="Proxy between Claude Code and Amazon Bedrock with automatic failover",
    version="0.1.0",
    lifespan=lifespan,
)


from .config import get_settings

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_allowed_origins,
    allow_credentials=_settings.cors_allow_credentials,
    allow_methods=_settings.cors_allowed_methods,
    allow_headers=_settings.cors_allowed_headers,
)

app.include_router(proxy_router)
app.include_router(admin_auth_router)
app.include_router(admin_users_router)
app.include_router(admin_keys_router)
app.include_router(admin_usage_router)
app.include_router(admin_pricing_router)
app.include_router(admin_models_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(HTTPException)
async def http_exception_logger(request: Request, exc: HTTPException):
    return await http_exception_handler(request, exc)
