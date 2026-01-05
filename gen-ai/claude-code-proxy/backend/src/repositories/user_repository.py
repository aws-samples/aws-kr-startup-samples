from datetime import datetime
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import UserModel
from decimal import Decimal

from ..domain import User, UserStatus, RoutingStrategy


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        description: str | None = None,
        routing_strategy: RoutingStrategy = RoutingStrategy.PLAN_FIRST,
        monthly_budget_usd: Decimal | None = None,
    ) -> User:
        now = datetime.utcnow()
        model = UserModel(
            name=name,
            description=description,
            status=UserStatus.ACTIVE.value,
            routing_strategy=routing_strategy.value,
            monthly_budget_usd=monthly_budget_usd,
            created_at=now,
            updated_at=now,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.deleted_at.is_(None),
                UserModel.status != UserStatus.DELETED.value,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_active(self, limit: int = 100, offset: int = 0) -> list[User]:
        result = await self.session.execute(
            select(UserModel)
            .where(
                UserModel.deleted_at.is_(None),
                UserModel.status != UserStatus.DELETED.value,
            )
            .order_by(UserModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(m) for m in result.scalars()]

    async def update_status(self, user_id: UUID, status: UserStatus) -> bool:
        now = datetime.utcnow()
        extra = {"deleted_at": now} if status == UserStatus.DELETED else {}
        result = await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(status=status.value, updated_at=now, **extra)
        )
        return result.rowcount > 0

    async def update_budget(self, user_id: UUID, budget: Decimal | None) -> bool:
        now = datetime.utcnow()
        result = await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(monthly_budget_usd=budget, updated_at=now)
        )
        return result.rowcount > 0

    async def update_routing_strategy(
        self, user_id: UUID, routing_strategy: RoutingStrategy
    ) -> bool:
        now = datetime.utcnow()
        result = await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(routing_strategy=routing_strategy.value, updated_at=now)
        )
        return result.rowcount > 0

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            name=model.name,
            description=model.description,
            status=UserStatus(model.status),
            routing_strategy=RoutingStrategy(model.routing_strategy),
            monthly_budget_usd=model.monthly_budget_usd,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )
