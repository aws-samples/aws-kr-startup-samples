from .proxy_router import router as proxy_router
from .admin_auth import router as admin_auth_router
from .admin_users import router as admin_users_router
from .admin_keys import router as admin_keys_router
from .admin_usage import router as admin_usage_router
from .admin_pricing import router as admin_pricing_router
from .admin_model_slots import router as admin_model_slots_router
from .admin_model_pricing import router as admin_model_pricing_router
from .auth_sso import router as auth_sso_router
from .admin_groups import router as admin_groups_router

__all__ = [
    "proxy_router",
    "admin_auth_router",
    "admin_users_router",
    "admin_keys_router",
    "admin_usage_router",
    "admin_pricing_router",
    "admin_model_slots_router",
    "admin_model_pricing_router",
    "auth_sso_router",
    "admin_groups_router",
]
