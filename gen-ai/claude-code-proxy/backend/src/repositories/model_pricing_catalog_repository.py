from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ModelPricingCatalogModel


class ModelPricingCatalogRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_all(
        self,
        *,
        provider: str | None = None,
        region: str | None = None,
        include_inactive: bool = False,
    ) -> list[ModelPricingCatalogModel]:
        query = select(ModelPricingCatalogModel).order_by(
            ModelPricingCatalogModel.provider,
            ModelPricingCatalogModel.region,
            ModelPricingCatalogModel.model_id,
        )
        if provider:
            query = query.where(ModelPricingCatalogModel.provider == provider)
        if region:
            query = query.where(ModelPricingCatalogModel.region == region)
        if not include_inactive:
            query = query.where(ModelPricingCatalogModel.is_active)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, pricing_id: UUID) -> ModelPricingCatalogModel | None:
        result = await self._session.execute(
            select(ModelPricingCatalogModel).where(ModelPricingCatalogModel.id == pricing_id)
        )
        return result.scalar_one_or_none()

    async def get_by_lookup(
        self, *, provider: str, region: str, model_id: str
    ) -> ModelPricingCatalogModel | None:
        result = await self._session.execute(
            select(ModelPricingCatalogModel).where(
                ModelPricingCatalogModel.provider == provider,
                ModelPricingCatalogModel.region == region,
                ModelPricingCatalogModel.model_id == model_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        provider: str,
        region: str,
        model_id: str,
        input_price_per_million,
        output_price_per_million,
        cache_write_price_per_million,
        cache_write_1h_price_per_million,
        cache_read_price_per_million,
        effective_date,
        is_active: bool = True,
    ) -> ModelPricingCatalogModel:
        model = ModelPricingCatalogModel(
            provider=provider,
            region=region,
            model_id=model_id,
            input_price_per_million=input_price_per_million,
            output_price_per_million=output_price_per_million,
            cache_write_price_per_million=cache_write_price_per_million,
            cache_write_1h_price_per_million=cache_write_1h_price_per_million,
            cache_read_price_per_million=cache_read_price_per_million,
            effective_date=effective_date,
            is_active=is_active,
            updated_at=datetime.now(timezone.utc),
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(
        self,
        pricing_id: UUID,
        *,
        provider: str | None = None,
        region: str | None = None,
        model_id: str | None = None,
        input_price_per_million=None,
        output_price_per_million=None,
        cache_write_price_per_million=None,
        cache_write_1h_price_per_million=None,
        cache_read_price_per_million=None,
        effective_date=None,
        is_active: bool | None = None,
    ) -> ModelPricingCatalogModel | None:
        values = {"updated_at": datetime.now(timezone.utc)}
        if provider is not None:
            values["provider"] = provider
        if region is not None:
            values["region"] = region
        if model_id is not None:
            values["model_id"] = model_id
        if input_price_per_million is not None:
            values["input_price_per_million"] = input_price_per_million
        if output_price_per_million is not None:
            values["output_price_per_million"] = output_price_per_million
        if cache_write_price_per_million is not None:
            values["cache_write_price_per_million"] = cache_write_price_per_million
        if cache_write_1h_price_per_million is not None:
            values["cache_write_1h_price_per_million"] = cache_write_1h_price_per_million
        if cache_read_price_per_million is not None:
            values["cache_read_price_per_million"] = cache_read_price_per_million
        if effective_date is not None:
            values["effective_date"] = effective_date
        if is_active is not None:
            values["is_active"] = is_active
        result = await self._session.execute(
            update(ModelPricingCatalogModel)
            .where(ModelPricingCatalogModel.id == pricing_id)
            .values(**values)
        )
        if result.rowcount == 0:
            return None
        return await self.get_by_id(pricing_id)

    async def delete(self, pricing_id: UUID) -> bool:
        result = await self._session.execute(
            delete(ModelPricingCatalogModel).where(ModelPricingCatalogModel.id == pricing_id)
        )
        return result.rowcount > 0
