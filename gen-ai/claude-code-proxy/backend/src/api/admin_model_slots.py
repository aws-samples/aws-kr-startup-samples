from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..domain import ModelSlotResponse, ModelSlotUpdate
from ..proxy import get_proxy_deps
from ..proxy.model_mapping import (
    build_default_bedrock_model_resolver,
    set_cached_model_slots,
)
from ..repositories import ModelSlotRepository
from .deps import require_admin

router = APIRouter(
    prefix="/admin/model-slots", tags=["model-slots"], dependencies=[Depends(require_admin)]
)


async def _reload_model_resolver(session: AsyncSession) -> None:
    slot_repo = ModelSlotRepository(session)
    slots = await slot_repo.get_slot_mapping()
    set_cached_model_slots(slots)
    get_proxy_deps().bedrock_model_resolver = build_default_bedrock_model_resolver(model_slots=slots)


@router.get("", response_model=list[ModelSlotResponse])
async def list_model_slots(
    session: AsyncSession = Depends(get_session),
):
    repo = ModelSlotRepository(session)
    rows = await repo.list_all()
    return [
        ModelSlotResponse(
            id=row.id,
            slot=row.slot,
            bedrock_model_id=row.bedrock_model_id,
            description=row.description,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.put("/{slot}", response_model=ModelSlotResponse)
async def update_model_slot(
    slot: str,
    data: ModelSlotUpdate,
    session: AsyncSession = Depends(get_session),
):
    if slot not in {"opus", "sonnet", "haiku"}:
        raise HTTPException(status_code=404, detail="Model slot not found")

    repo = ModelSlotRepository(session)
    existing = await repo.get_by_slot(slot)
    if not existing:
        raise HTTPException(status_code=404, detail="Model slot not found")

    updated = await repo.update_slot(
        slot,
        bedrock_model_id=data.bedrock_model_id,
        description=data.description,
    )
    await session.commit()
    await _reload_model_resolver(session)

    return ModelSlotResponse(
        id=updated.id,
        slot=updated.slot,
        bedrock_model_id=updated.bedrock_model_id,
        description=updated.description,
        updated_at=updated.updated_at,
    )
