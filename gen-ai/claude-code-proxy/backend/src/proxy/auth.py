import uuid
from uuid import UUID
from dataclasses import dataclass
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..domain import RoutingStrategy
from ..repositories import AccessKeyRepository, BedrockKeyRepository
from ..security import KeyHasher
from .context import RequestContext
from .dependencies import get_proxy_deps


@dataclass
class _CachedAccessKey:
    user_id: UUID
    access_key_id: UUID
    access_key_prefix: str
    bedrock_region: str
    bedrock_model: str
    has_bedrock_key: bool
    routing_strategy: RoutingStrategy


class AuthService:
    """Access key authentication service."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._hasher = KeyHasher()
        self._access_key_repo = AccessKeyRepository(session)
        self._bedrock_key_repo = BedrockKeyRepository(session)

    async def authenticate(self, raw_key: str) -> RequestContext | None:
        key_hash = self._hasher.hash(raw_key)
        cache = get_proxy_deps().access_key_cache

        # Check cache
        cached: _CachedAccessKey | None = cache.get(key_hash)
        if cached:
            return RequestContext(
                request_id=f"req_{uuid.uuid4().hex[:16]}",
                user_id=cached.user_id,
                access_key_id=cached.access_key_id,
                access_key_prefix=cached.access_key_prefix,
                bedrock_region=cached.bedrock_region,
                bedrock_model=cached.bedrock_model,
                has_bedrock_key=cached.has_bedrock_key,
                routing_strategy=cached.routing_strategy,
            )

        # Query database
        result = await self._access_key_repo.get_by_hash_with_user(key_hash)
        if not result:
            return None

        access_key, user_id, routing_strategy_str = result

        bedrock_key = await self._bedrock_key_repo.get_by_access_key_id(access_key.id)
        has_bedrock_key = bedrock_key is not None
        routing_strategy = RoutingStrategy(routing_strategy_str)

        cached_entry = _CachedAccessKey(
            user_id=user_id,
            access_key_id=access_key.id,
            access_key_prefix=access_key.key_prefix,
            bedrock_region=access_key.bedrock_region,
            bedrock_model=access_key.bedrock_model,
            has_bedrock_key=has_bedrock_key,
            routing_strategy=routing_strategy,
        )

        # Cache result
        cache.set(key_hash, cached_entry)
        return RequestContext(
            request_id=f"req_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            access_key_id=access_key.id,
            access_key_prefix=access_key.key_prefix,
            bedrock_region=access_key.bedrock_region,
            bedrock_model=access_key.bedrock_model,
            has_bedrock_key=has_bedrock_key,
            routing_strategy=routing_strategy,
        )


def invalidate_access_key_cache(key_hash: str) -> None:
    get_proxy_deps().access_key_cache.invalidate(key_hash)


async def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session)
