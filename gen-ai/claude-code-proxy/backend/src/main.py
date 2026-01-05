from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .logging import setup_logging
from .api import (
    proxy_router,
    admin_auth_router,
    admin_users_router,
    admin_keys_router,
    admin_usage_router,
    admin_pricing_router,
)

setup_logging()

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
