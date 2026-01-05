from datetime import datetime
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import BedrockKeyModel
from ..domain import BedrockKey


class BedrockKeyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, access_key_id: UUID, encrypted_key: bytes, key_hash: str
    ) -> BedrockKey:
        model = BedrockKeyModel(
            access_key_id=access_key_id,
            encrypted_key=encrypted_key,
            key_hash=key_hash,
            created_at=datetime.utcnow(),
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def get_by_access_key_id(self, access_key_id: UUID) -> BedrockKey | None:
        result = await self.session.execute(
            select(BedrockKeyModel).where(BedrockKeyModel.access_key_id == access_key_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(
        self, access_key_id: UUID, encrypted_key: bytes, key_hash: str
    ) -> BedrockKey | None:
        result = await self.session.execute(
            select(BedrockKeyModel).where(BedrockKeyModel.access_key_id == access_key_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        model.encrypted_key = encrypted_key
        model.key_hash = key_hash
        model.rotated_at = datetime.utcnow()
        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, access_key_id: UUID) -> bool:
        result = await self.session.execute(
            delete(BedrockKeyModel).where(BedrockKeyModel.access_key_id == access_key_id)
        )
        return result.rowcount > 0

    async def list_access_key_ids(self, access_key_ids: list[UUID]) -> set[UUID]:
        if not access_key_ids:
            return set()
        result = await self.session.execute(
            select(BedrockKeyModel.access_key_id).where(
                BedrockKeyModel.access_key_id.in_(access_key_ids)
            )
        )
        return set(result.scalars().all())

    def _to_entity(self, model: BedrockKeyModel) -> BedrockKey:
        return BedrockKey(
            access_key_id=model.access_key_id,
            encrypted_key=model.encrypted_key,
            key_hash=model.key_hash,
            created_at=model.created_at,
            rotated_at=model.rotated_at,
        )
