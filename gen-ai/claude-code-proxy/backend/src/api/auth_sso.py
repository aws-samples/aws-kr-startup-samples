"""SSO authentication endpoint.

API Gateway (IAM Auth) validates SigV4 and forwards the caller's ARN
in the ``x-sso-arn`` header.  This endpoint:

1. Parses the SSO ARN to extract the username.
2. Finds or creates a proxy user + access_key.
3. Returns the raw access_key for use by apiKeyHelper.

Security: Only API Gateway should set ``x-sso-arn``.  Direct calls
without a valid ARN are rejected.
"""

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..domain import CachingStrategy, KeyStatus, RoutingStrategy
from ..logging import get_logger
from ..proxy.model_mapping import get_effective_slot_model
from ..repositories import AccessKeyRepository, GroupRepository, UserRepository
from ..security import KeyGenerator, KeyHasher

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["sso"])

_SSO_ARN_HEADER = "x-sso-arn"

# arn:aws:sts::<account>:assumed-role/AWSReservedSSO_<role>_<hash>/<username>
_SSO_ARN_PATTERN = re.compile(
    r"^arn:aws:sts::(\d+):assumed-role/AWSReservedSSO_([^_]+)_[^/]+/(.+)$"
)


def _parse_sso_arn(arn: str) -> tuple[str, str, str] | None:
    """Parse SSO ARN → (username, role_name, account_id) or None."""
    match = _SSO_ARN_PATTERN.match(arn)
    if not match:
        return None
    return match.group(3), match.group(2), match.group(1)


@router.post("/sso")
async def sso_authenticate(
    raw_request: Request,
    session: AsyncSession = Depends(get_session),
):
    arn = raw_request.headers.get(_SSO_ARN_HEADER)
    if not arn:
        raise HTTPException(status_code=401, detail=f"Missing {_SSO_ARN_HEADER} header")

    parsed = _parse_sso_arn(arn)
    if not parsed:
        raise HTTPException(status_code=400, detail="Invalid SSO ARN format")

    username, role_name, account_id = parsed
    logger.info("sso_auth", username=username, role=role_name, account=account_id)

    user_repo = UserRepository(session)
    key_repo = AccessKeyRepository(session)
    group_repo = GroupRepository(session)
    hasher = KeyHasher()

    # Find or create group from Permission Set name
    group, group_created = await group_repo.get_or_create(
        name=role_name,
        description=f"Auto-created from SSO Permission Set: {role_name}",
    )
    if group_created:
        logger.info("sso_group_created", group_name=role_name, group_id=str(group.id))

    # Find or create user
    user = await user_repo.get_by_name(username)
    if not user:
        user = await user_repo.create(
            name=username,
            description=f"SSO user (role={role_name}, account={account_id})",
            routing_strategy=RoutingStrategy.BEDROCK_ONLY,
            caching_strategy=CachingStrategy.FIVE_MINUTES,
            group_id=group.id,
        )
        logger.info("sso_user_created", username=username, user_id=str(user.id))
    elif user.group_id != group.id:
        # Permission Set changed — update group assignment
        await user_repo.update_group(user.id, group.id)
        logger.info("sso_user_group_updated", username=username, group_name=role_name)

    # Find existing active key or create new one
    keys = await key_repo.list_by_user(user.id)
    active_keys = [k for k in keys if k.status == KeyStatus.ACTIVE]

    if active_keys:
        # Return existing key — but we can't recover raw_key from hash.
        # Generate a new key and revoke old ones.
        pass

    # Always generate a fresh key (apiKeyHelper calls this periodically)
    raw_key = KeyGenerator.generate()
    key_hash = hasher.hash(raw_key)
    key_prefix = KeyGenerator.get_prefix(raw_key)

    # Revoke previous keys for this user
    for k in active_keys:
        await key_repo.revoke(k.id)

    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.token_ttl_hours)

    await key_repo.create(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        bedrock_region="",
        bedrock_model=get_effective_slot_model("sonnet"),
        expires_at=expires_at,
    )
    await session.commit()

    return {
        "access_key": raw_key,
        "username": username,
        "group": role_name,
        "expires_at": expires_at.isoformat(),
    }
