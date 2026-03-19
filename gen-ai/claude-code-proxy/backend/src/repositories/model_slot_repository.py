from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ModelSlotModel


class ModelSlotRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_all(self) -> list[ModelSlotModel]:
        result = await self._session.execute(select(ModelSlotModel).order_by(ModelSlotModel.slot))
        return list(result.scalars().all())

    async def get_by_slot(self, slot: str) -> ModelSlotModel | None:
        result = await self._session.execute(
            select(ModelSlotModel).where(ModelSlotModel.slot == slot)
        )
        return result.scalar_one_or_none()

    async def update_slot(
        self,
        slot: str,
        *,
        bedrock_model_id: str,
        description: str | None = None,
    ) -> ModelSlotModel | None:
        values = {
            "bedrock_model_id": bedrock_model_id,
            "updated_at": datetime.now(timezone.utc),
        }
        if description is not None:
            values["description"] = description
        result = await self._session.execute(
            update(ModelSlotModel).where(ModelSlotModel.slot == slot).values(**values)
        )
        if result.rowcount == 0:
            return None
        return await self.get_by_slot(slot)

    async def get_slot_mapping(self) -> dict[str, str]:
        rows = await self.list_all()
        return {row.slot: row.bedrock_model_id for row in rows}
