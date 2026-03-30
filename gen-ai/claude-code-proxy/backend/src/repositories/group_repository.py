from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import GroupModel, UserModel
from ..domain import Group


class GroupRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        description: str | None = None,
        monthly_budget_usd: Decimal | None = None,
        allowed_models: str | None = None,
    ) -> Group:
        now = datetime.utcnow()
        model = GroupModel(
            name=name,
            description=description,
            monthly_budget_usd=monthly_budget_usd,
            allowed_models=allowed_models,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def get_by_id(self, group_id: UUID) -> Group | None:
        result = await self.session.execute(
            select(GroupModel).where(
                GroupModel.id == group_id,
                GroupModel.status != "deleted",
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_name(self, name: str) -> Group | None:
        result = await self.session.execute(
            select(GroupModel).where(
                GroupModel.name == name,
                GroupModel.status != "deleted",
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_or_create(
        self, name: str, description: str | None = None
    ) -> tuple[Group, bool]:
        """Find or create group. Returns (group, was_created)."""
        group = await self.get_by_name(name)
        if group:
            return group, False
        group = await self.create(name=name, description=description)
        return group, True

    async def list_active(self, limit: int = 100, offset: int = 0) -> list[Group]:
        result = await self.session.execute(
            select(GroupModel)
            .where(GroupModel.status != "deleted")
            .order_by(GroupModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(m) for m in result.scalars()]

    async def get_member_count(self, group_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(UserModel.id)).where(
                UserModel.group_id == group_id,
                UserModel.status == "active",
                UserModel.deleted_at.is_(None),
            )
        )
        return result.scalar_one() or 0

    async def get_members(self, group_id: UUID, limit: int = 100, offset: int = 0) -> list:
        from ..domain import User, UserStatus, RoutingStrategy, CachingStrategy

        result = await self.session.execute(
            select(UserModel)
            .where(
                UserModel.group_id == group_id,
                UserModel.status != "deleted",
                UserModel.deleted_at.is_(None),
            )
            .order_by(UserModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [
            User(
                id=m.id,
                name=m.name,
                description=m.description,
                status=UserStatus(m.status),
                routing_strategy=RoutingStrategy(m.routing_strategy),
                caching_strategy=CachingStrategy(m.caching_strategy),
                monthly_budget_usd=m.monthly_budget_usd,
                group_id=m.group_id,
                created_at=m.created_at,
                updated_at=m.updated_at,
                deleted_at=m.deleted_at,
            )
            for m in result.scalars()
        ]

    async def update_budget(self, group_id: UUID, budget: Decimal | None) -> bool:
        result = await self.session.execute(
            update(GroupModel)
            .where(GroupModel.id == group_id)
            .values(monthly_budget_usd=budget, updated_at=datetime.utcnow())
        )
        return result.rowcount > 0

    async def update(self, group_id: UUID, **fields) -> bool:
        fields["updated_at"] = datetime.utcnow()
        result = await self.session.execute(
            update(GroupModel).where(GroupModel.id == group_id).values(**fields)
        )
        return result.rowcount > 0

    async def delete(self, group_id: UUID) -> bool:
        return await self.update(group_id, status="deleted")

    def _to_entity(self, model: GroupModel) -> Group:
        return Group(
            id=model.id,
            name=model.name,
            description=model.description,
            monthly_budget_usd=model.monthly_budget_usd,
            allowed_models=model.allowed_models,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
