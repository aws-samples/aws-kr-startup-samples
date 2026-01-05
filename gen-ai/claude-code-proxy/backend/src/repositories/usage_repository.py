from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ..db.models import TokenUsageModel, UsageAggregateModel, UserModel
from ..domain import TokenUsage, UsageAggregate, UserStatus


class TokenUsageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        request_id: str,
        user_id: UUID,
        access_key_id: UUID,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        is_fallback: bool,
        latency_ms: int,
        cache_read_input_tokens: int | None = None,
        cache_creation_input_tokens: int | None = None,
        estimated_cost_usd: Decimal = Decimal("0"),
        input_cost_usd: Decimal = Decimal("0"),
        output_cost_usd: Decimal = Decimal("0"),
        cache_write_cost_usd: Decimal = Decimal("0"),
        cache_read_cost_usd: Decimal = Decimal("0"),
        pricing_region: str = "ap-northeast-2",
        pricing_model_id: str = "",
        pricing_effective_date: date | None = None,
        pricing_input_price_per_million: Decimal = Decimal("0"),
        pricing_output_price_per_million: Decimal = Decimal("0"),
        pricing_cache_write_price_per_million: Decimal = Decimal("0"),
        pricing_cache_read_price_per_million: Decimal = Decimal("0"),
    ) -> TokenUsage:
        db_model = TokenUsageModel(
            id=uuid4(),
            request_id=request_id,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            access_key_id=access_key_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            total_tokens=total_tokens,
            provider="bedrock",
            is_fallback=is_fallback,
            latency_ms=latency_ms,
            estimated_cost_usd=estimated_cost_usd,
            input_cost_usd=input_cost_usd,
            output_cost_usd=output_cost_usd,
            cache_write_cost_usd=cache_write_cost_usd,
            cache_read_cost_usd=cache_read_cost_usd,
            pricing_region=pricing_region,
            pricing_model_id=pricing_model_id,
            pricing_effective_date=pricing_effective_date,
            pricing_input_price_per_million=pricing_input_price_per_million,
            pricing_output_price_per_million=pricing_output_price_per_million,
            pricing_cache_write_price_per_million=pricing_cache_write_price_per_million,
            pricing_cache_read_price_per_million=pricing_cache_read_price_per_million,
        )
        self.session.add(db_model)
        await self.session.flush()
        return self._to_entity(db_model)

    def _to_entity(self, model: TokenUsageModel) -> TokenUsage:
        return TokenUsage(
            id=model.id,
            request_id=model.request_id,
            timestamp=model.timestamp,
            user_id=model.user_id,
            access_key_id=model.access_key_id,
            model=model.model,
            input_tokens=model.input_tokens,
            output_tokens=model.output_tokens,
            cache_read_input_tokens=model.cache_read_input_tokens,
            cache_creation_input_tokens=model.cache_creation_input_tokens,
            total_tokens=model.total_tokens,
            provider=model.provider,
            is_fallback=model.is_fallback,
            latency_ms=model.latency_ms,
            estimated_cost_usd=model.estimated_cost_usd,
            input_cost_usd=model.input_cost_usd,
            output_cost_usd=model.output_cost_usd,
            cache_write_cost_usd=model.cache_write_cost_usd,
            cache_read_cost_usd=model.cache_read_cost_usd,
            pricing_region=model.pricing_region,
            pricing_model_id=model.pricing_model_id,
            pricing_effective_date=model.pricing_effective_date,
            pricing_input_price_per_million=model.pricing_input_price_per_million,
            pricing_output_price_per_million=model.pricing_output_price_per_million,
            pricing_cache_write_price_per_million=model.pricing_cache_write_price_per_million,
            pricing_cache_read_price_per_million=model.pricing_cache_read_price_per_million,
        )

    async def get_cost_breakdown_by_model(
        self,
        start_time: datetime,
        end_time: datetime,
        user_id: UUID | None = None,
        access_key_id: UUID | None = None,
    ) -> list[dict]:
        query = select(
            TokenUsageModel.pricing_model_id.label("pricing_model_id"),
            func.sum(TokenUsageModel.input_cost_usd).label("input_cost_usd"),
            func.sum(TokenUsageModel.output_cost_usd).label("output_cost_usd"),
            func.sum(TokenUsageModel.cache_write_cost_usd).label("cache_write_cost_usd"),
            func.sum(TokenUsageModel.cache_read_cost_usd).label("cache_read_cost_usd"),
            func.sum(TokenUsageModel.estimated_cost_usd).label("total_cost_usd"),
        ).where(
            TokenUsageModel.timestamp >= start_time,
            TokenUsageModel.timestamp < end_time,
        )
        if user_id:
            query = query.where(TokenUsageModel.user_id == user_id)
        if access_key_id:
            query = query.where(TokenUsageModel.access_key_id == access_key_id)
        query = query.group_by(TokenUsageModel.pricing_model_id).order_by(
            TokenUsageModel.pricing_model_id
        )

        result = await self.session.execute(query)
        return [
            {
                "pricing_model_id": row.pricing_model_id,
                "input_cost_usd": row.input_cost_usd or Decimal("0"),
                "output_cost_usd": row.output_cost_usd or Decimal("0"),
                "cache_write_cost_usd": row.cache_write_cost_usd or Decimal("0"),
                "cache_read_cost_usd": row.cache_read_cost_usd or Decimal("0"),
                "total_cost_usd": row.total_cost_usd or Decimal("0"),
            }
            for row in result
        ]


class UsageAggregateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def query(
        self,
        bucket_type: str,
        start_time: datetime,
        end_time: datetime,
        user_id: UUID | None = None,
        access_key_id: UUID | None = None,
    ) -> list[UsageAggregate]:
        query = select(UsageAggregateModel).where(
            UsageAggregateModel.bucket_type == bucket_type,
            UsageAggregateModel.bucket_start >= start_time,
            UsageAggregateModel.bucket_start < end_time,
        )
        if user_id:
            query = query.where(UsageAggregateModel.user_id == user_id)
        if access_key_id:
            query = query.where(UsageAggregateModel.access_key_id == access_key_id)
        query = query.order_by(UsageAggregateModel.bucket_start)

        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars()]

    async def query_bucket_totals(
        self,
        bucket_type: str,
        start_time: datetime,
        end_time: datetime,
        user_id: UUID | None = None,
        access_key_id: UUID | None = None,
    ) -> list[dict]:
        query = select(
            UsageAggregateModel.bucket_start.label("bucket_start"),
            func.sum(UsageAggregateModel.total_requests).label("total_requests"),
            func.sum(UsageAggregateModel.total_input_tokens).label("total_input_tokens"),
            func.sum(UsageAggregateModel.total_output_tokens).label("total_output_tokens"),
            func.sum(UsageAggregateModel.total_tokens).label("total_tokens"),
            func.sum(UsageAggregateModel.total_cache_write_tokens).label(
                "total_cache_write_tokens"
            ),
            func.sum(UsageAggregateModel.total_cache_read_tokens).label(
                "total_cache_read_tokens"
            ),
            func.sum(UsageAggregateModel.total_input_cost_usd).label("total_input_cost_usd"),
            func.sum(UsageAggregateModel.total_output_cost_usd).label("total_output_cost_usd"),
            func.sum(UsageAggregateModel.total_cache_write_cost_usd).label(
                "total_cache_write_cost_usd"
            ),
            func.sum(UsageAggregateModel.total_cache_read_cost_usd).label(
                "total_cache_read_cost_usd"
            ),
            func.sum(UsageAggregateModel.total_estimated_cost_usd).label(
                "total_estimated_cost_usd"
            ),
        ).where(
            UsageAggregateModel.bucket_type == bucket_type,
            UsageAggregateModel.bucket_start >= start_time,
            UsageAggregateModel.bucket_start < end_time,
        )
        if user_id:
            query = query.where(UsageAggregateModel.user_id == user_id)
        if access_key_id:
            query = query.where(UsageAggregateModel.access_key_id == access_key_id)

        query = query.group_by(UsageAggregateModel.bucket_start).order_by(
            UsageAggregateModel.bucket_start
        )
        result = await self.session.execute(query)
        return [
            {
                "bucket_start": row.bucket_start,
                "total_requests": row.total_requests or 0,
                "total_input_tokens": row.total_input_tokens or 0,
                "total_output_tokens": row.total_output_tokens or 0,
                "total_tokens": row.total_tokens or 0,
                "total_cache_write_tokens": row.total_cache_write_tokens or 0,
                "total_cache_read_tokens": row.total_cache_read_tokens or 0,
                "total_input_cost_usd": row.total_input_cost_usd or Decimal("0"),
                "total_output_cost_usd": row.total_output_cost_usd or Decimal("0"),
                "total_cache_write_cost_usd": row.total_cache_write_cost_usd or Decimal("0"),
                "total_cache_read_cost_usd": row.total_cache_read_cost_usd or Decimal("0"),
                "total_estimated_cost_usd": row.total_estimated_cost_usd or Decimal("0"),
            }
            for row in result
        ]

    async def get_totals(
        self,
        bucket_type: str,
        start_time: datetime,
        end_time: datetime,
        user_id: UUID | None = None,
        access_key_id: UUID | None = None,
    ) -> dict:
        query = select(
            func.sum(UsageAggregateModel.total_requests),
            func.sum(UsageAggregateModel.total_input_tokens),
            func.sum(UsageAggregateModel.total_output_tokens),
            func.sum(UsageAggregateModel.total_tokens),
            func.sum(UsageAggregateModel.total_cache_write_tokens),
            func.sum(UsageAggregateModel.total_cache_read_tokens),
            func.sum(UsageAggregateModel.total_input_cost_usd),
            func.sum(UsageAggregateModel.total_output_cost_usd),
            func.sum(UsageAggregateModel.total_cache_write_cost_usd),
            func.sum(UsageAggregateModel.total_cache_read_cost_usd),
            func.sum(UsageAggregateModel.total_estimated_cost_usd),
        ).where(
            UsageAggregateModel.bucket_type == bucket_type,
            UsageAggregateModel.bucket_start >= start_time,
            UsageAggregateModel.bucket_start < end_time,
        )
        if user_id:
            query = query.where(UsageAggregateModel.user_id == user_id)
        if access_key_id:
            query = query.where(UsageAggregateModel.access_key_id == access_key_id)

        result = await self.session.execute(query)
        row = result.one()
        return {
            "total_requests": row[0] or 0,
            "total_input_tokens": row[1] or 0,
            "total_output_tokens": row[2] or 0,
            "total_tokens": row[3] or 0,
            "total_cache_write_tokens": row[4] or 0,
            "total_cache_read_tokens": row[5] or 0,
            "total_input_cost_usd": row[6] or Decimal("0"),
            "total_output_cost_usd": row[7] or Decimal("0"),
            "total_cache_write_cost_usd": row[8] or Decimal("0"),
            "total_cache_read_cost_usd": row[9] or Decimal("0"),
            "total_estimated_cost_usd": row[10] or Decimal("0"),
        }

    async def get_monthly_usage_total(
        self,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> Decimal:
        query = select(func.sum(UsageAggregateModel.total_estimated_cost_usd)).where(
            UsageAggregateModel.bucket_type == "month",
            UsageAggregateModel.bucket_start >= start_time,
            UsageAggregateModel.bucket_start < end_time,
            UsageAggregateModel.user_id == user_id,
        )
        result = await self.session.execute(query)
        total = result.scalar_one_or_none()
        return total or Decimal("0")

    async def increment(
        self,
        bucket_type: str,
        bucket_start: datetime,
        user_id: UUID,
        access_key_id: UUID,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cache_write_tokens: int = 0,
        cache_read_tokens: int = 0,
        total_estimated_cost_usd: Decimal = Decimal("0"),
        total_input_cost_usd: Decimal = Decimal("0"),
        total_output_cost_usd: Decimal = Decimal("0"),
        total_cache_write_cost_usd: Decimal = Decimal("0"),
        total_cache_read_cost_usd: Decimal = Decimal("0"),
    ) -> None:
        stmt = insert(UsageAggregateModel).values(
            id=uuid4(),
            bucket_type=bucket_type,
            bucket_start=bucket_start,
            user_id=user_id,
            access_key_id=access_key_id,
            total_requests=1,
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            total_tokens=total_tokens,
            total_cache_write_tokens=cache_write_tokens,
            total_cache_read_tokens=cache_read_tokens,
            total_input_cost_usd=total_input_cost_usd,
            total_output_cost_usd=total_output_cost_usd,
            total_cache_write_cost_usd=total_cache_write_cost_usd,
            total_cache_read_cost_usd=total_cache_read_cost_usd,
            total_estimated_cost_usd=total_estimated_cost_usd,
        ).on_conflict_do_update(
            index_elements=["bucket_type", "bucket_start", "user_id", "access_key_id"],
            set_={
                "total_requests": UsageAggregateModel.total_requests + 1,
                "total_input_tokens": UsageAggregateModel.total_input_tokens + input_tokens,
                "total_output_tokens": UsageAggregateModel.total_output_tokens + output_tokens,
                "total_tokens": UsageAggregateModel.total_tokens + total_tokens,
                "total_cache_write_tokens": UsageAggregateModel.total_cache_write_tokens
                + cache_write_tokens,
                "total_cache_read_tokens": UsageAggregateModel.total_cache_read_tokens
                + cache_read_tokens,
                "total_input_cost_usd": UsageAggregateModel.total_input_cost_usd
                + total_input_cost_usd,
                "total_output_cost_usd": UsageAggregateModel.total_output_cost_usd
                + total_output_cost_usd,
                "total_cache_write_cost_usd": UsageAggregateModel.total_cache_write_cost_usd
                + total_cache_write_cost_usd,
                "total_cache_read_cost_usd": UsageAggregateModel.total_cache_read_cost_usd
                + total_cache_read_cost_usd,
                "total_estimated_cost_usd": UsageAggregateModel.total_estimated_cost_usd
                + total_estimated_cost_usd,
            },
        )
        await self.session.execute(stmt)

    async def get_top_users(
        self,
        bucket_type: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10,
    ) -> list[dict]:
        query = (
            select(
                UsageAggregateModel.user_id.label("user_id"),
                UserModel.name.label("name"),
                func.sum(UsageAggregateModel.total_tokens).label("total_tokens"),
                func.sum(UsageAggregateModel.total_requests).label("total_requests"),
            )
            .join(UserModel, UsageAggregateModel.user_id == UserModel.id)
            .where(
                UsageAggregateModel.bucket_type == bucket_type,
                UsageAggregateModel.bucket_start >= start_time,
                UsageAggregateModel.bucket_start < end_time,
                UserModel.deleted_at.is_(None),
                UserModel.status != UserStatus.DELETED.value,
            )
            .group_by(UsageAggregateModel.user_id, UserModel.name)
            .order_by(desc(func.sum(UsageAggregateModel.total_tokens)))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return [
            {
                "user_id": row.user_id,
                "name": row.name,
                "total_tokens": row.total_tokens or 0,
                "total_requests": row.total_requests or 0,
            }
            for row in result
        ]

    def _to_entity(self, model: UsageAggregateModel) -> UsageAggregate:
        return UsageAggregate(
            id=model.id,
            bucket_type=model.bucket_type,
            bucket_start=model.bucket_start,
            user_id=model.user_id,
            access_key_id=model.access_key_id,
            total_requests=model.total_requests,
            total_input_tokens=model.total_input_tokens,
            total_output_tokens=model.total_output_tokens,
            total_tokens=model.total_tokens,
            total_cache_write_tokens=model.total_cache_write_tokens,
            total_cache_read_tokens=model.total_cache_read_tokens,
            total_input_cost_usd=model.total_input_cost_usd,
            total_output_cost_usd=model.total_output_cost_usd,
            total_cache_write_cost_usd=model.total_cache_write_cost_usd,
            total_cache_read_cost_usd=model.total_cache_read_cost_usd,
            total_estimated_cost_usd=model.total_estimated_cost_usd,
        )
