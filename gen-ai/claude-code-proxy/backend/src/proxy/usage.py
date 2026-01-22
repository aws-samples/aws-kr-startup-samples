"""Usage recording to database."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..domain import AnthropicUsage, CostCalculator, PricingConfig, Provider
from ..repositories import TokenUsageRepository, UsageAggregateRepository
from .context import RequestContext
from .router import ProxyResponse
from .metrics import CloudWatchMetricsEmitter


def _get_bucket_start(ts: datetime, bucket_type: str, tz: ZoneInfo) -> datetime:
    local_ts = ts.astimezone(tz)
    if bucket_type == "minute":
        return local_ts.replace(second=0, microsecond=0)
    elif bucket_type == "hour":
        return local_ts.replace(minute=0, second=0, microsecond=0)
    elif bucket_type == "day":
        return local_ts.replace(hour=0, minute=0, second=0, microsecond=0)
    elif bucket_type == "week":
        # Sunday start for week buckets in KST.
        days_since_sunday = (local_ts.weekday() + 1) % 7
        return (local_ts - timedelta(days=days_since_sunday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif bucket_type == "month":
        return local_ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return local_ts.replace(minute=0, second=0, microsecond=0)


class UsageRecorder:
    """Records usage to database and emits metrics."""

    KST = ZoneInfo("Asia/Seoul")

    def __init__(
        self,
        token_usage_repo: TokenUsageRepository,
        usage_aggregate_repo: UsageAggregateRepository,
        metrics_emitter: CloudWatchMetricsEmitter | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self._repo = token_usage_repo
        self._agg_repo = usage_aggregate_repo
        self._metrics = metrics_emitter or CloudWatchMetricsEmitter()
        self._session_factory = session_factory

    async def record(
        self,
        ctx: RequestContext,
        response: ProxyResponse,
        latency_ms: int,
        model: str,
    ) -> None:
        # Emit metrics (fire and forget)
        asyncio.create_task(self._metrics.emit(response, latency_ms))

        # Record token usage to DB for successful responses
        if response.success and response.usage:
            await asyncio.shield(
                self._record_usage_with_cost(
                    ctx, response, latency_ms, model, provider=response.provider
                )
            )

    async def record_streaming_usage(
        self,
        ctx: RequestContext,
        usage: AnthropicUsage,
        latency_ms: int,
        model: str,
        is_fallback: bool,
        provider: Provider = "bedrock",
    ) -> None:
        response = ProxyResponse(
            success=True,
            response=None,
            usage=usage,
            provider=provider,
            is_fallback=is_fallback,
            status_code=200,
        )
        await self._record_usage_with_cost(
            ctx, response, latency_ms, model, provider=provider
        )

    async def _record_usage_with_cost(
        self,
        ctx: RequestContext,
        response: ProxyResponse,
        latency_ms: int,
        model: str,
        provider: Provider,
    ) -> None:
        try:
            now_utc = datetime.now(timezone.utc)
            now_kst = now_utc.astimezone(self.KST)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cache_write_tokens = response.usage.cache_creation_input_tokens or 0
            cache_read_tokens = response.usage.cache_read_input_tokens or 0
            total_tokens = input_tokens + output_tokens

            pricing_region = ctx.bedrock_region if provider == "bedrock" else "global"
            cost_breakdown, pricing = self._calculate_cost_safe(
                model,
                pricing_region,
                provider,
                input_tokens,
                output_tokens,
                cache_write_tokens,
                cache_read_tokens,
            )
            pricing_model_id = (
                pricing.model_id if pricing else PricingConfig.normalize_model_id(model)
            )

            if self._session_factory:
                async with self._session_factory() as session:
                    try:
                        token_repo = TokenUsageRepository(session)
                        agg_repo = UsageAggregateRepository(session)
                        await self._persist_usage(
                            token_repo=token_repo,
                            agg_repo=agg_repo,
                            ctx=ctx,
                            response=response,
                            latency_ms=latency_ms,
                            model=model,
                            provider=provider,
                            pricing=pricing,
                            pricing_model_id=pricing_model_id,
                            cost_breakdown=cost_breakdown,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            total_tokens=total_tokens,
                            cache_write_tokens=cache_write_tokens,
                            cache_read_tokens=cache_read_tokens,
                            now_kst=now_kst,
                        )
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise
            else:
                await self._persist_usage(
                    token_repo=self._repo,
                    agg_repo=self._agg_repo,
                    ctx=ctx,
                    response=response,
                    latency_ms=latency_ms,
                    model=model,
                    provider=provider,
                    pricing=pricing,
                    pricing_model_id=pricing_model_id,
                    cost_breakdown=cost_breakdown,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cache_write_tokens=cache_write_tokens,
                    cache_read_tokens=cache_read_tokens,
                    now_kst=now_kst,
                )
        except Exception:
            pass

    def _calculate_cost_safe(
        self,
        model: str,
        region: str,
        provider: Provider,
        input_tokens: int,
        output_tokens: int,
        cache_write_tokens: int,
        cache_read_tokens: int,
    ):
        try:
            pricing = PricingConfig.get_pricing(
                model, region=region, provider=provider
            )
            if pricing:
                return (
                    CostCalculator.calculate_cost(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cache_write_tokens=cache_write_tokens,
                        cache_read_tokens=cache_read_tokens,
                        pricing=pricing,
                    ),
                    pricing,
                )
        except Exception:
            pass

        return CostCalculator.zero_cost(), None

    async def _persist_usage(
        self,
        token_repo: TokenUsageRepository,
        agg_repo: UsageAggregateRepository,
        ctx: RequestContext,
        response: ProxyResponse,
        latency_ms: int,
        model: str,
        provider: Provider,
        pricing,
        pricing_model_id: str,
        cost_breakdown,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cache_write_tokens: int,
        cache_read_tokens: int,
        now_kst: datetime,
    ) -> None:
        await token_repo.create(
            request_id=ctx.request_id,
            user_id=ctx.user_id,
            access_key_id=ctx.access_key_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            is_fallback=response.is_fallback,
            latency_ms=latency_ms,
            cache_read_input_tokens=response.usage.cache_read_input_tokens,
            cache_creation_input_tokens=response.usage.cache_creation_input_tokens,
            estimated_cost_usd=cost_breakdown.total_cost,
            input_cost_usd=cost_breakdown.input_cost,
            output_cost_usd=cost_breakdown.output_cost,
            cache_write_cost_usd=cost_breakdown.cache_write_cost,
            cache_read_cost_usd=cost_breakdown.cache_read_cost,
            pricing_region=pricing.region if pricing else "global"
            if provider == "plan"
            else ctx.bedrock_region,
            pricing_model_id=pricing_model_id,
            pricing_effective_date=pricing.effective_date if pricing else None,
            pricing_input_price_per_million=pricing.input_price_per_million
            if pricing
            else Decimal("0"),
            pricing_output_price_per_million=pricing.output_price_per_million
            if pricing
            else Decimal("0"),
            pricing_cache_write_price_per_million=pricing.cache_write_price_per_million
            if pricing
            else Decimal("0"),
            pricing_cache_read_price_per_million=pricing.cache_read_price_per_million
            if pricing
            else Decimal("0"),
        )

        for bucket_type in ("minute", "hour", "day", "week", "month"):
            bucket_start_kst = _get_bucket_start(now_kst, bucket_type, tz=self.KST)
            bucket_start = bucket_start_kst.astimezone(timezone.utc)
            await agg_repo.increment(
                bucket_type=bucket_type,
                bucket_start=bucket_start,
                user_id=ctx.user_id,
                access_key_id=ctx.access_key_id,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cache_write_tokens=cache_write_tokens,
                cache_read_tokens=cache_read_tokens,
                total_estimated_cost_usd=cost_breakdown.total_cost,
                total_input_cost_usd=cost_breakdown.input_cost,
                total_output_cost_usd=cost_breakdown.output_cost,
                total_cache_write_cost_usd=cost_breakdown.cache_write_cost,
                total_cache_read_cost_usd=cost_breakdown.cache_read_cost,
            )
