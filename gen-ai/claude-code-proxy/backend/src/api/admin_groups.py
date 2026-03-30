from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..domain import (
    GroupBudgetResponse,
    GroupBudgetUpdate,
    GroupCreate,
    GroupResponse,
    GroupUpdate,
)
from ..proxy.budget import BudgetService
from ..repositories import GroupRepository, UserRepository, UsageAggregateRepository
from .deps import require_admin

router = APIRouter(prefix="/admin/groups", tags=["admin-groups"], dependencies=[Depends(require_admin)])


def _format_usd(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def _to_group_response(group, member_count: int = 0) -> GroupResponse:
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        monthly_budget_usd=_format_usd(group.monthly_budget_usd) if group.monthly_budget_usd else None,
        allowed_models=group.allowed_models,
        status=group.status,
        member_count=member_count,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.get("/")
async def list_groups(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    repo = GroupRepository(session)
    groups = await repo.list_active(limit=limit, offset=offset)
    results = []
    for g in groups:
        count = await repo.get_member_count(g.id)
        results.append(_to_group_response(g, member_count=count))
    return results


@router.post("/", status_code=201)
async def create_group(
    body: GroupCreate,
    session: AsyncSession = Depends(get_session),
):
    repo = GroupRepository(session)
    existing = await repo.get_by_name(body.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Group '{body.name}' already exists")
    group = await repo.create(
        name=body.name,
        description=body.description,
        monthly_budget_usd=body.monthly_budget_usd,
        allowed_models=body.allowed_models,
    )
    await session.commit()
    return _to_group_response(group)


@router.get("/{group_id}")
async def get_group(
    group_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = GroupRepository(session)
    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    count = await repo.get_member_count(group_id)
    return _to_group_response(group, member_count=count)


@router.put("/{group_id}")
async def update_group(
    group_id: UUID,
    body: GroupUpdate,
    session: AsyncSession = Depends(get_session),
):
    repo = GroupRepository(session)
    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    fields = body.model_dump(exclude_unset=True)
    if fields:
        await repo.update(group_id, **fields)
        await session.commit()
    group = await repo.get_by_id(group_id)
    count = await repo.get_member_count(group_id)
    return _to_group_response(group, member_count=count)


@router.delete("/{group_id}")
async def delete_group(
    group_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = GroupRepository(session)
    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await repo.delete(group_id)
    await session.commit()
    return {"status": "deleted", "group_id": str(group_id)}


@router.get("/{group_id}/budget")
async def get_group_budget(
    group_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    group_repo = GroupRepository(session)
    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    budget_service = BudgetService(
        UserRepository(session),
        UsageAggregateRepository(session),
        group_repo=group_repo,
    )
    result = await budget_service._check_group_budget(
        group_id, *budget_service.get_month_window()
    )
    period_start, period_end_exclusive = budget_service.get_month_window()
    from datetime import timedelta
    period_end = period_end_exclusive - timedelta(seconds=1)

    return GroupBudgetResponse(
        group_id=group_id,
        group_name=group.name,
        monthly_budget_usd=_format_usd(group.monthly_budget_usd) if group.monthly_budget_usd else None,
        current_usage_usd=_format_usd(result.current_usage),
        remaining_usd=_format_usd(result.remaining) if result.remaining is not None else None,
        usage_percentage=result.usage_percentage,
        period_start=period_start,
        period_end=period_end,
    )


@router.put("/{group_id}/budget")
async def update_group_budget(
    group_id: UUID,
    body: GroupBudgetUpdate,
    session: AsyncSession = Depends(get_session),
):
    group_repo = GroupRepository(session)
    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await group_repo.update_budget(group_id, body.monthly_budget_usd)
    await session.commit()

    # Invalidate group budget cache
    from ..proxy.budget import get_proxy_deps
    get_proxy_deps().budget_cache.invalidate(f"group:{group_id}")

    # Return updated budget
    return await get_group_budget(group_id, session)


@router.get("/{group_id}/members")
async def get_group_members(
    group_id: UUID,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    group_repo = GroupRepository(session)
    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    members = await group_repo.get_members(group_id, limit=limit, offset=offset)
    return [
        {
            "user_id": str(m.id),
            "name": m.name,
            "status": m.status.value,
        }
        for m in members
    ]


@router.get("/{group_id}/usage")
async def get_group_usage(
    group_id: UUID,
    period: str = "current_month",
    session: AsyncSession = Depends(get_session),
):
    group_repo = GroupRepository(session)
    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    usage_repo = UsageAggregateRepository(session)
    budget_service = BudgetService(
        UserRepository(session), usage_repo, group_repo=group_repo
    )
    period_start, period_end = budget_service.get_month_window()

    from datetime import timezone
    start_utc = period_start.astimezone(timezone.utc)
    end_utc = period_end.astimezone(timezone.utc)

    total = await usage_repo.get_group_monthly_usage_total(
        group_id, start_utc, end_utc, provider="bedrock"
    )

    return {
        "group_id": str(group_id),
        "group_name": group.name,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "total_estimated_cost_usd": _format_usd(total),
    }
