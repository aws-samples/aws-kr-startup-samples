from datetime import datetime
from uuid import UUID
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..db.models import AccessKeyModel
from ..domain import AccessKey, KeyStatus


class AccessKeyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: UUID,
        key_hash: str,
        key_prefix: str,
        bedrock_region: str,
        bedrock_model: str,
    ) -> AccessKey:
        model = AccessKeyModel(
            user_id=user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            status=KeyStatus.ACTIVE.value,
            bedrock_region=bedrock_region,
            bedrock_model=bedrock_model,
            created_at=datetime.utcnow(),
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def get_by_hash(self, key_hash: str) -> AccessKey | None:
        result = await self.session.execute(
            select(AccessKeyModel).where(AccessKeyModel.key_hash == key_hash)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_hash_with_user(
        self, key_hash: str
    ) -> tuple[AccessKey, UUID, str] | None:
        """Returns (access_key, user_id, routing_strategy) or None."""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(AccessKeyModel)
            .options(joinedload(AccessKeyModel.user))
            .where(
                AccessKeyModel.key_hash == key_hash,
                or_(
                    AccessKeyModel.status == KeyStatus.ACTIVE.value,
                    # ROTATING keys must not be expired
                    (
                        AccessKeyModel.status == KeyStatus.ROTATING.value
                    ) & (
                        (AccessKeyModel.rotation_expires_at == None) |
                        (AccessKeyModel.rotation_expires_at > now)
                    ),
                ),
            )
        )
        model = result.scalar_one_or_none()
        if not model or model.user.status != "active":
            return None
        return self._to_entity(model), model.user_id, model.user.routing_strategy

    async def get_by_id(self, key_id: UUID) -> AccessKey | None:
        result = await self.session.execute(
            select(AccessKeyModel).where(AccessKeyModel.id == key_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_user(self, user_id: UUID) -> list[AccessKey]:
        result = await self.session.execute(
            select(AccessKeyModel)
            .where(AccessKeyModel.user_id == user_id)
            .order_by(AccessKeyModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars()]

    async def revoke(self, key_id: UUID) -> bool:
        result = await self.session.execute(
            update(AccessKeyModel)
            .where(AccessKeyModel.id == key_id)
            .values(status=KeyStatus.REVOKED.value, revoked_at=datetime.utcnow())
        )
        return result.rowcount > 0

    async def set_rotating(self, key_id: UUID, expires_at: datetime) -> bool:
        result = await self.session.execute(
            update(AccessKeyModel)
            .where(AccessKeyModel.id == key_id)
            .values(status=KeyStatus.ROTATING.value, rotation_expires_at=expires_at)
        )
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        result = await self.session.execute(
            update(AccessKeyModel)
            .where(
                AccessKeyModel.user_id == user_id,
                AccessKeyModel.status != KeyStatus.REVOKED.value,
            )
            .values(status=KeyStatus.REVOKED.value, revoked_at=datetime.utcnow())
        )
        return result.rowcount

    def _to_entity(self, model: AccessKeyModel) -> AccessKey:
        return AccessKey(
            id=model.id,
            user_id=model.user_id,
            key_hash=model.key_hash,
            key_prefix=model.key_prefix,
            status=KeyStatus(model.status),
            bedrock_region=model.bedrock_region,
            bedrock_model=model.bedrock_model,
            created_at=model.created_at,
            revoked_at=model.revoked_at,
            rotation_expires_at=model.rotation_expires_at,
        )
