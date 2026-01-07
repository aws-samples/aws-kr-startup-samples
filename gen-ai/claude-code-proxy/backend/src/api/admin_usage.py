from uuid import UUID
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..domain import (
    UsageResponse,
    UsageBucket,
    UsageTopUser,
    UsageTopUserSeries,
    UsageTopUserSeriesBucket,
    CostBreakdownByModel,
)
from ..repositories import UsageAggregateRepository, TokenUsageRepository
from .deps import require_admin

router = APIRouter(prefix="/admin/usage", tags=["usage"], dependencies=[Depends(require_admin)])
KST = ZoneInfo("Asia/Seoul")


def _get_week_start_kst(ts: datetime) -> datetime:
    days_since_sunday = (ts.weekday() + 1) % 7
    return (ts - timedelta(days=days_since_sunday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _resolve_time_range(
    period: str | None,
    start_date: date | None,
    end_date: date | None,
    now_utc: datetime | None = None,
) -> tuple[datetime, datetime]:
    now_utc = now_utc or datetime.now(timezone.utc)
    now_kst = now_utc.astimezone(KST)

    has_start = start_date is not None
    has_end = end_date is not None
    if has_start ^ has_end:
        raise HTTPException(status_code=400, detail="Invalid date range")

    if has_start and has_end:
        start_kst = datetime.combine(start_date, time.min, tzinfo=KST)
        end_kst = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=KST)
    elif period:
        if period == "day":
            start_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_kst = _get_week_start_kst(now_kst)
        elif period == "month":
            start_kst = now_kst.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise HTTPException(status_code=400, detail="Invalid period")
        end_kst = now_kst
    else:
        end_kst = now_kst
        start_kst = now_kst - timedelta(hours=24)

    return start_kst.astimezone(timezone.utc), end_kst.astimezone(timezone.utc)


@router.get("", response_model=UsageResponse)
async def get_usage(
    user_id: UUID | None = None,
    team_id: UUID | None = None,
    access_key_id: UUID | None = None,
    bucket_type: str = Query(default="hour", pattern="^(minute|hour|day|week|month)$"),
    period: str | None = Query(default=None, pattern="^(day|week|month)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_session),
):
    if user_id and team_id and user_id != team_id:
        raise HTTPException(status_code=400, detail="Conflicting user_id and team_id")

    effective_user_id = user_id or team_id

    repo = UsageAggregateRepository(session)
    token_repo = TokenUsageRepository(session)

    start_time, end_time = _resolve_time_range(period, start_date, end_date)

    aggregates = await repo.query_bucket_totals(
        bucket_type=bucket_type,
        start_time=start_time,
        end_time=end_time,
        user_id=effective_user_id,
        access_key_id=access_key_id,
    )

    totals = await repo.get_totals(
        bucket_type=bucket_type,
        start_time=start_time,
        end_time=end_time,
        user_id=effective_user_id,
        access_key_id=access_key_id,
    )

    breakdown_rows = await token_repo.get_cost_breakdown_by_model(
        start_time=start_time,
        end_time=end_time,
        user_id=effective_user_id,
        access_key_id=access_key_id,
    )

    buckets = [
        UsageBucket(
            bucket_start=a["bucket_start"],
            requests=a["total_requests"],
            input_tokens=a["total_input_tokens"],
            output_tokens=a["total_output_tokens"],
            total_tokens=a["total_tokens"],
            cache_write_tokens=a["total_cache_write_tokens"],
            cache_read_tokens=a["total_cache_read_tokens"],
            input_cost_usd=str(a["total_input_cost_usd"]),
            output_cost_usd=str(a["total_output_cost_usd"]),
            cache_write_cost_usd=str(a["total_cache_write_cost_usd"]),
            cache_read_cost_usd=str(a["total_cache_read_cost_usd"]),
            estimated_cost_usd=str(a["total_estimated_cost_usd"]),
        )
        for a in aggregates
    ]

    return UsageResponse(
        buckets=buckets,
        total_requests=totals["total_requests"],
        total_input_tokens=totals["total_input_tokens"],
        total_output_tokens=totals["total_output_tokens"],
        total_tokens=totals["total_tokens"],
        total_cache_write_tokens=totals["total_cache_write_tokens"],
        total_cache_read_tokens=totals["total_cache_read_tokens"],
        total_input_cost_usd=str(totals["total_input_cost_usd"]),
        total_output_cost_usd=str(totals["total_output_cost_usd"]),
        total_cache_write_cost_usd=str(totals["total_cache_write_cost_usd"]),
        total_cache_read_cost_usd=str(totals["total_cache_read_cost_usd"]),
        estimated_cost_usd=str(totals["total_estimated_cost_usd"]),
        cost_breakdown=[
            CostBreakdownByModel(
                model_id=row["pricing_model_id"],
                total_cost_usd=str(row["total_cost_usd"]),
                input_cost_usd=str(row["input_cost_usd"]),
                output_cost_usd=str(row["output_cost_usd"]),
                cache_write_cost_usd=str(row["cache_write_cost_usd"]),
                cache_read_cost_usd=str(row["cache_read_cost_usd"]),
            )
            for row in breakdown_rows
        ],
    )


@router.get("/top-users", response_model=list[UsageTopUser])
async def get_top_users(
    bucket_type: str = Query(default="hour", pattern="^(minute|hour|day|week|month)$"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
):
    repo = UsageAggregateRepository(session)

    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)

    results = await repo.get_top_users(
        bucket_type=bucket_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    return [
        UsageTopUser(
            user_id=row["user_id"],
            name=row["name"],
            total_tokens=row["total_tokens"],
            total_requests=row["total_requests"],
        )
        for row in results
    ]


@router.get("/top-users/series", response_model=list[UsageTopUserSeries])
async def get_top_user_series(
    bucket_type: str = Query(default="hour", pattern="^(minute|hour|day|week|month)$"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
):
    repo = UsageAggregateRepository(session)

    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)

    top_users = await repo.get_top_users(
        bucket_type=bucket_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    user_ids = [row["user_id"] for row in top_users]
    series_rows = await repo.get_user_series(
        bucket_type=bucket_type,
        start_time=start_time,
        end_time=end_time,
        user_ids=user_ids,
    )

    user_map = {
        row["user_id"]: UsageTopUserSeries(
            user_id=row["user_id"], name=row["name"], buckets=[]
        )
        for row in top_users
    }
    for row in series_rows:
        user = user_map.get(row["user_id"])
        if not user:
            continue
        user.buckets.append(
            UsageTopUserSeriesBucket(
                bucket_start=row["bucket_start"],
                total_tokens=row["total_tokens"],
            )
        )

    return list(user_map.values())
