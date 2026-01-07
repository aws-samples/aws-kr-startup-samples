from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ModelMappingModel


class ModelMappingRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_all(self, include_inactive: bool = False) -> list[ModelMappingModel]:
        query = select(ModelMappingModel).order_by(ModelMappingModel.claude_model)
        if not include_inactive:
            query = query.where(ModelMappingModel.is_active == True)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, mapping_id: UUID) -> ModelMappingModel | None:
        query = select(ModelMappingModel).where(ModelMappingModel.id == mapping_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_claude_model(self, claude_model: str) -> ModelMappingModel | None:
        query = select(ModelMappingModel).where(
            ModelMappingModel.claude_model == claude_model
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        claude_model: str,
        bedrock_model: str,
        description: str | None = None,
        is_active: bool = True,
    ) -> ModelMappingModel:
        now = datetime.now(timezone.utc)
        mapping = ModelMappingModel(
            claude_model=claude_model,
            bedrock_model=bedrock_model,
            description=description,
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        self._session.add(mapping)
        await self._session.flush()
        return mapping

    async def update(
        self,
        mapping_id: UUID,
        bedrock_model: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> bool:
        values: dict = {"updated_at": datetime.now(timezone.utc)}
        if bedrock_model is not None:
            values["bedrock_model"] = bedrock_model
        if description is not None:
            values["description"] = description
        if is_active is not None:
            values["is_active"] = is_active

        query = (
            update(ModelMappingModel)
            .where(ModelMappingModel.id == mapping_id)
            .values(**values)
        )
        result = await self._session.execute(query)
        return result.rowcount > 0

    async def delete(self, mapping_id: UUID) -> bool:
        query = delete(ModelMappingModel).where(ModelMappingModel.id == mapping_id)
        result = await self._session.execute(query)
        return result.rowcount > 0

    async def get_active_mappings_dict(self) -> dict[str, str]:
        mappings = await self.list_all(include_inactive=False)
        return {m.claude_model: m.bedrock_model for m in mappings}
