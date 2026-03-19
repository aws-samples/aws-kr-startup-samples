from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..domain import (
    ModelPricingCatalogCreate,
    ModelPricingCatalogResponse,
    ModelPricingCatalogUpdate,
)
from ..domain.pricing import PricingConfig
from ..repositories import ModelPricingCatalogRepository, ModelSlotRepository
from .deps import require_admin

router = APIRouter(
    prefix="/admin/model-pricing", tags=["model-pricing"], dependencies=[Depends(require_admin)]
)


async def _reload_pricing_catalog(session: AsyncSession) -> None:
    repo = ModelPricingCatalogRepository(session)
    rows = await repo.list_all(include_inactive=False)
    PricingConfig.set_catalog_pricing(PricingConfig.build_pricing_data_from_entries(rows))


def _to_response(row) -> ModelPricingCatalogResponse:
    return ModelPricingCatalogResponse(
        id=row.id,
        provider=row.provider,
        region=row.region,
        model_id=row.model_id,
        input_price_per_million=row.input_price_per_million,
        output_price_per_million=row.output_price_per_million,
        cache_write_price_per_million=row.cache_write_price_per_million,
        cache_write_1h_price_per_million=row.cache_write_1h_price_per_million,
        cache_read_price_per_million=row.cache_read_price_per_million,
        effective_date=row.effective_date,
        is_active=row.is_active,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[ModelPricingCatalogResponse])
async def list_model_pricing(
    provider: str | None = Query(default=None),
    region: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
):
    repo = ModelPricingCatalogRepository(session)
    rows = await repo.list_all(
        provider=provider,
        region=region,
        include_inactive=include_inactive,
    )
    return [_to_response(row) for row in rows]


@router.post("", response_model=ModelPricingCatalogResponse, status_code=201)
async def create_model_pricing(
    data: ModelPricingCatalogCreate,
    session: AsyncSession = Depends(get_session),
):
    repo = ModelPricingCatalogRepository(session)
    existing = await repo.get_by_lookup(
        provider=data.provider,
        region=data.region,
        model_id=data.model_id,
    )
    if existing:
        raise HTTPException(status_code=409, detail="Pricing entry already exists")

    created = await repo.create(
        provider=data.provider,
        region=data.region,
        model_id=data.model_id,
        input_price_per_million=data.input_price_per_million,
        output_price_per_million=data.output_price_per_million,
        cache_write_price_per_million=data.cache_write_price_per_million,
        cache_write_1h_price_per_million=data.cache_write_1h_price_per_million,
        cache_read_price_per_million=data.cache_read_price_per_million,
        effective_date=date.fromisoformat(data.effective_date),
        is_active=data.is_active,
    )
    await session.commit()
    await _reload_pricing_catalog(session)
    return _to_response(created)


@router.put("/{pricing_id}", response_model=ModelPricingCatalogResponse)
async def update_model_pricing(
    pricing_id: UUID,
    data: ModelPricingCatalogUpdate,
    session: AsyncSession = Depends(get_session),
):
    repo = ModelPricingCatalogRepository(session)
    existing = await repo.get_by_id(pricing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Pricing entry not found")

    updated = await repo.update(
        pricing_id,
        provider=data.provider,
        region=data.region,
        model_id=data.model_id,
        input_price_per_million=data.input_price_per_million,
        output_price_per_million=data.output_price_per_million,
        cache_write_price_per_million=data.cache_write_price_per_million,
        cache_write_1h_price_per_million=data.cache_write_1h_price_per_million,
        cache_read_price_per_million=data.cache_read_price_per_million,
        effective_date=date.fromisoformat(data.effective_date) if data.effective_date else None,
        is_active=data.is_active,
    )
    await session.commit()
    await _reload_pricing_catalog(session)
    return _to_response(updated)


@router.delete("/{pricing_id}", status_code=204)
async def delete_model_pricing(
    pricing_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = ModelPricingCatalogRepository(session)
    slot_repo = ModelSlotRepository(session)
    existing = await repo.get_by_id(pricing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Pricing entry not found")

    if existing.provider == "bedrock":
        slots = await slot_repo.list_all()
        if any(slot.bedrock_model_id == existing.model_id for slot in slots):
            raise HTTPException(
                status_code=409,
                detail="Pricing entry is referenced by an active model slot",
            )

    await repo.delete(pricing_id)
    await session.commit()
    await _reload_pricing_catalog(session)
