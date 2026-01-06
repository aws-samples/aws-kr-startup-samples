from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..domain import (
    UserCreate,
    UserResponse,
    UserStatus,
    UserBudgetUpdate,
    UserBudgetResponse,
    UserRoutingStrategyUpdate,
    RoutingStrategy,
    KeyStatus,
)
from ..repositories import (
    UserRepository,
    AccessKeyRepository,
    UsageAggregateRepository,
    BedrockKeyRepository,
)
from ..proxy import invalidate_access_key_cache, BudgetService, BudgetCheckResult, invalidate_budget_cache
from .deps import require_admin

router = APIRouter(prefix="/admin/users", tags=["users"], dependencies=[Depends(require_admin)])


def _build_budget_response(user_id: UUID, result: BudgetCheckResult) -> UserBudgetResponse:
    return UserBudgetResponse(
        user_id=user_id,
        monthly_budget_usd=str(result.monthly_budget)
        if result.monthly_budget is not None
        else None,
        current_usage_usd=str(result.current_usage),
        remaining_usd=str(result.remaining) if result.remaining is not None else None,
        usage_percentage=result.usage_percentage,
        period_start=result.period_start,
        period_end=result.period_end,
    )


async def _ensure_bedrock_keys_for_routing(
    user_id: UUID,
    key_repo: AccessKeyRepository,
    bedrock_repo: BedrockKeyRepository,
) -> None:
    keys = await key_repo.list_by_user(user_id)
    valid_keys = [
        key for key in keys if key.status in (KeyStatus.ACTIVE, KeyStatus.ROTATING)
    ]
    if not valid_keys:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "NO_ACCESS_KEYS",
                "message": "At least one active access key is required before enabling bedrock_only routing",
            },
        )
    bedrock_ids = await bedrock_repo.list_access_key_ids([key.id for key in valid_keys])
    if any(key.id not in bedrock_ids for key in valid_keys):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_BEDROCK_KEYS",
                "message": "Bedrock credentials must be registered for all active access keys before enabling bedrock_only routing",
            },
        )


@router.get("", response_model=list[UserResponse])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    users = await repo.list_active(limit=limit, offset=offset)
    return [UserResponse(**u.__dict__) for u in users]


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    if data.routing_strategy == RoutingStrategy.BEDROCK_ONLY.value:
        raise HTTPException(
            status_code=400,
            detail="Bedrock key required before enabling bedrock_only routing",
        )
    repo = UserRepository(session)
    user = await repo.create(
        name=data.name,
        description=data.description,
        routing_strategy=RoutingStrategy(data.routing_strategy),
        monthly_budget_usd=data.monthly_budget_usd,
    )
    if session is not None:
        await session.commit()
    return UserResponse(**user.__dict__)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user or user.status == UserStatus.DELETED:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user.__dict__)


@router.get("/{user_id}/budget", response_model=UserBudgetResponse)
async def get_user_budget(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    user_repo = UserRepository(session)
    usage_repo = UsageAggregateRepository(session)

    user = await user_repo.get_by_id(user_id)
    if not user or user.status == UserStatus.DELETED:
        raise HTTPException(status_code=404, detail="User not found")

    budget_service = BudgetService(user_repo, usage_repo)
    result = await budget_service.check_budget(user_id, fail_open=False)
    return _build_budget_response(user_id, result)


@router.put("/{user_id}/budget", response_model=UserBudgetResponse)
async def update_user_budget(
    user_id: UUID,
    data: UserBudgetUpdate,
    session: AsyncSession = Depends(get_session),
):
    user_repo = UserRepository(session)
    usage_repo = UsageAggregateRepository(session)

    user = await user_repo.get_by_id(user_id)
    if not user or user.status == UserStatus.DELETED:
        raise HTTPException(status_code=404, detail="User not found")

    updated = await user_repo.update_budget(user_id, data.monthly_budget_usd)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    if session is not None:
        await session.commit()
    invalidate_budget_cache(user_id)

    budget_service = BudgetService(user_repo, usage_repo)
    result = await budget_service.check_budget(user_id, fail_open=False)
    return _build_budget_response(user_id, result)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    user_repo = UserRepository(session)
    key_repo = AccessKeyRepository(session)

    user = await user_repo.get_by_id(user_id)
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="User not found or not active")

    # Get all keys before revoking to invalidate cache
    keys = await key_repo.list_by_user(user_id)

    await user_repo.update_status(user_id, UserStatus.INACTIVE)
    await key_repo.revoke_all_for_user(user_id)
    await session.commit()

    # Invalidate cache for all user's keys
    for key in keys:
        invalidate_access_key_cache(key.key_hash)

    user = await user_repo.get_by_id(user_id)
    return UserResponse(**user.__dict__)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    user_repo = UserRepository(session)
    key_repo = AccessKeyRepository(session)

    user = await user_repo.get_by_id(user_id)
    if not user or user.status == UserStatus.DELETED:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all keys before revoking to invalidate cache
    keys = await key_repo.list_by_user(user_id)

    await user_repo.update_status(user_id, UserStatus.DELETED)
    await key_repo.revoke_all_for_user(user_id)
    await session.commit()

    # Invalidate cache for all user's keys
    for key in keys:
        invalidate_access_key_cache(key.key_hash)


@router.put("/{user_id}/routing-strategy", response_model=UserResponse)
async def update_user_routing_strategy(
    user_id: UUID,
    data: UserRoutingStrategyUpdate,
    session: AsyncSession = Depends(get_session),
):
    user_repo = UserRepository(session)
    key_repo = AccessKeyRepository(session)
    bedrock_repo = BedrockKeyRepository(session)

    user = await user_repo.get_by_id(user_id)
    if not user or user.status == UserStatus.DELETED:
        raise HTTPException(status_code=404, detail="User not found")

    routing_strategy = RoutingStrategy(data.routing_strategy)
    if routing_strategy == RoutingStrategy.BEDROCK_ONLY:
        await _ensure_bedrock_keys_for_routing(user_id, key_repo, bedrock_repo)

    updated = await user_repo.update_routing_strategy(user_id, routing_strategy)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    if session is not None:
        await session.commit()

    # Invalidate cache for all user's keys to pick up new routing strategy
    keys = await key_repo.list_by_user(user_id)
    for key in keys:
        invalidate_access_key_cache(key.key_hash)

    user = await user_repo.get_by_id(user_id)
    return UserResponse(**user.__dict__)
