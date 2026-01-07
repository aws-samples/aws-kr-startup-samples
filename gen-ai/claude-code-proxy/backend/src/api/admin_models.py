from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..domain import ModelMappingCreate, ModelMappingUpdate, ModelMappingResponse
from ..repositories import ModelMappingRepository
from ..proxy import invalidate_model_mapping_cache, get_proxy_deps
from ..proxy.model_mapping import set_cached_db_mappings, build_default_bedrock_model_resolver
from .deps import require_admin

router = APIRouter(
    prefix="/admin/models", tags=["models"], dependencies=[Depends(require_admin)]
)


async def _reload_model_resolver(session: AsyncSession) -> None:
    """Reload the model resolver with latest DB mappings."""
    repo = ModelMappingRepository(session)
    db_mappings = await repo.get_active_mappings_dict()
    set_cached_db_mappings(db_mappings)

    deps = get_proxy_deps()
    deps.bedrock_model_resolver = build_default_bedrock_model_resolver(db_mappings)


@router.get("/mappings", response_model=list[ModelMappingResponse])
async def list_model_mappings(
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
):
    repo = ModelMappingRepository(session)
    mappings = await repo.list_all(include_inactive=include_inactive)
    return [ModelMappingResponse(**m.__dict__) for m in mappings]


@router.post("/mappings", response_model=ModelMappingResponse, status_code=201)
async def create_model_mapping(
    data: ModelMappingCreate,
    session: AsyncSession = Depends(get_session),
):
    repo = ModelMappingRepository(session)

    existing = await repo.get_by_claude_model(data.claude_model)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Mapping for claude model '{data.claude_model}' already exists",
        )

    mapping = await repo.create(
        claude_model=data.claude_model,
        bedrock_model=data.bedrock_model,
        description=data.description,
        is_active=data.is_active,
    )
    await session.commit()
    await _reload_model_resolver(session)
    return ModelMappingResponse(**mapping.__dict__)


@router.get("/mappings/{mapping_id}", response_model=ModelMappingResponse)
async def get_model_mapping(
    mapping_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = ModelMappingRepository(session)
    mapping = await repo.get_by_id(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Model mapping not found")
    return ModelMappingResponse(**mapping.__dict__)


@router.put("/mappings/{mapping_id}", response_model=ModelMappingResponse)
async def update_model_mapping(
    mapping_id: UUID,
    data: ModelMappingUpdate,
    session: AsyncSession = Depends(get_session),
):
    repo = ModelMappingRepository(session)

    mapping = await repo.get_by_id(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Model mapping not found")

    updated = await repo.update(
        mapping_id=mapping_id,
        bedrock_model=data.bedrock_model,
        description=data.description,
        is_active=data.is_active,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Model mapping not found")

    await session.commit()
    await _reload_model_resolver(session)

    mapping = await repo.get_by_id(mapping_id)
    return ModelMappingResponse(**mapping.__dict__)


@router.delete("/mappings/{mapping_id}", status_code=204)
async def delete_model_mapping(
    mapping_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = ModelMappingRepository(session)

    mapping = await repo.get_by_id(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Model mapping not found")

    await repo.delete(mapping_id)
    await session.commit()
    await _reload_model_resolver(session)
