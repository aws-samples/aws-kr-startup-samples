from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..domain import AccessKeyCreate, AccessKeyResponse, BedrockKeyRegister, KeyStatus
from ..repositories import AccessKeyRepository, BedrockKeyRepository, UserRepository
from ..security import KeyGenerator, KeyHasher, KMSEnvelopeEncryption
from ..proxy import invalidate_access_key_cache, invalidate_bedrock_key_cache
from ..proxy.model_mapping import DEFAULT_BEDROCK_MODEL
from .deps import require_admin

router = APIRouter(prefix="/admin", tags=["keys"], dependencies=[Depends(require_admin)])

ROTATION_GRACE_PERIOD = 300  # 5 minutes


@router.get("/users/{user_id}/access-keys", response_model=list[AccessKeyResponse])
async def list_access_keys(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = AccessKeyRepository(session)
    bedrock_repo = BedrockKeyRepository(session)
    keys = await repo.list_by_user(user_id)
    bedrock_ids = await bedrock_repo.list_access_key_ids([key.id for key in keys])
    return [
        AccessKeyResponse(**k.__dict__, has_bedrock_key=k.id in bedrock_ids)
        for k in keys
    ]


@router.post("/users/{user_id}/access-keys", response_model=AccessKeyResponse, status_code=201)
async def issue_access_key(
    user_id: UUID,
    data: AccessKeyCreate,
    session: AsyncSession = Depends(get_session),
):
    user_repo = UserRepository(session)
    key_repo = AccessKeyRepository(session)
    hasher = KeyHasher()

    user = await user_repo.get_by_id(user_id)
    if not user or user.status.value != "active":
        raise HTTPException(status_code=404, detail="User not found or not active")

    raw_key = KeyGenerator.generate()
    key_hash = hasher.hash(raw_key)
    key_prefix = KeyGenerator.get_prefix(raw_key)

    access_key = await key_repo.create(
        user_id=user_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        bedrock_region=data.bedrock_region,
        bedrock_model=data.bedrock_model or DEFAULT_BEDROCK_MODEL,
    )
    await session.commit()

    return AccessKeyResponse(
        **access_key.__dict__,
        raw_key=raw_key,
        has_bedrock_key=False,
    )


@router.delete("/access-keys/{key_id}", status_code=204)
async def revoke_access_key(
    key_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    key_repo = AccessKeyRepository(session)
    bedrock_repo = BedrockKeyRepository(session)

    key = await key_repo.get_by_id(key_id)
    if not key or key.status == KeyStatus.REVOKED:
        raise HTTPException(status_code=404, detail="Key not found")

    await key_repo.revoke(key_id)
    await bedrock_repo.delete(key_id)
    await session.commit()

    invalidate_access_key_cache(key.key_hash)
    invalidate_bedrock_key_cache(key_id)


@router.post("/access-keys/{key_id}/rotate", response_model=AccessKeyResponse)
async def rotate_access_key(
    key_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    key_repo = AccessKeyRepository(session)
    bedrock_repo = BedrockKeyRepository(session)
    hasher = KeyHasher()

    old_key = await key_repo.get_by_id(key_id)
    if not old_key or old_key.status == KeyStatus.REVOKED:
        raise HTTPException(status_code=404, detail="Key not found")

    # Set old key to rotating
    expires_at = datetime.utcnow() + timedelta(seconds=ROTATION_GRACE_PERIOD)
    await key_repo.set_rotating(key_id, expires_at)

    # Create new key
    raw_key = KeyGenerator.generate()
    key_hash = hasher.hash(raw_key)
    key_prefix = KeyGenerator.get_prefix(raw_key)

    new_key = await key_repo.create(
        user_id=old_key.user_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        bedrock_region=old_key.bedrock_region,
        bedrock_model=old_key.bedrock_model,
    )

    # Transfer Bedrock key from old to new access key
    old_bedrock_key = await bedrock_repo.get_by_access_key_id(key_id)
    if old_bedrock_key:
        await bedrock_repo.create(
            new_key.id, old_bedrock_key.encrypted_key, old_bedrock_key.key_hash
        )

    await session.commit()

    invalidate_access_key_cache(old_key.key_hash)

    return AccessKeyResponse(
        **new_key.__dict__,
        raw_key=raw_key,
        has_bedrock_key=old_bedrock_key is not None,
    )


@router.post("/access-keys/{key_id}/bedrock-key", status_code=201)
async def register_bedrock_key(
    key_id: UUID,
    data: BedrockKeyRegister,
    session: AsyncSession = Depends(get_session),
):
    key_repo = AccessKeyRepository(session)
    bedrock_repo = BedrockKeyRepository(session)
    hasher = KeyHasher()
    encryption = KMSEnvelopeEncryption()

    access_key = await key_repo.get_by_id(key_id)
    if not access_key or access_key.status == KeyStatus.REVOKED:
        raise HTTPException(status_code=404, detail="Access key not found")

    encrypted = encryption.encrypt(data.bedrock_api_key)
    key_hash = hasher.hash(data.bedrock_api_key)

    existing = await bedrock_repo.get_by_access_key_id(key_id)
    if existing:
        await bedrock_repo.update(key_id, encrypted, key_hash)
    else:
        await bedrock_repo.create(key_id, encrypted, key_hash)

    await session.commit()
    invalidate_bedrock_key_cache(key_id)

    return {"status": "registered"}
