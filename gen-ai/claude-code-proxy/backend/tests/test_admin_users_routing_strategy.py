from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api import admin_users
from src.domain import (
    AccessKey,
    KeyStatus,
    RoutingStrategy,
    User,
    UserCreate,
    UserRoutingStrategyUpdate,
    UserStatus,
)


@pytest.mark.asyncio
async def test_create_user_rejects_bedrock_only_without_keys() -> None:
    with pytest.raises(HTTPException) as exc:
        await admin_users.create_user(
            data=UserCreate(
                name="user",
                description=None,
                routing_strategy=RoutingStrategy.BEDROCK_ONLY.value,
                monthly_budget_usd=None,
            ),
            session=None,
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_user_routing_strategy_requires_bedrock_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    key_id = uuid4()

    class FakeUserRepository:
        def __init__(self, _session) -> None:
            self.user = User(
                id=user_id,
                name="user",
                description=None,
                status=UserStatus.ACTIVE,
                monthly_budget_usd=Decimal("10.00"),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

        async def get_by_id(self, _user_id):
            return self.user

        async def update_routing_strategy(self, _user_id, _strategy):
            return True

    class FakeAccessKeyRepository:
        def __init__(self, _session) -> None:
            self._keys = [
                AccessKey(
                    id=key_id,
                    user_id=user_id,
                    key_hash="hash",
                    key_prefix="ak",
                    status=KeyStatus.ACTIVE,
                    bedrock_region="ap-northeast-2",
                    bedrock_model="anthropic.claude-sonnet-4-5-20250514",
                    created_at=datetime.now(timezone.utc),
                )
            ]

        async def list_by_user(self, _user_id):
            return self._keys

    class FakeBedrockKeyRepository:
        def __init__(self, _session) -> None:
            return None

        async def list_access_key_ids(self, _access_key_ids):
            return set()

    monkeypatch.setattr(admin_users, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(admin_users, "AccessKeyRepository", FakeAccessKeyRepository)
    monkeypatch.setattr(admin_users, "BedrockKeyRepository", FakeBedrockKeyRepository)

    with pytest.raises(HTTPException) as exc:
        await admin_users.update_user_routing_strategy(
            user_id=user_id,
            data=UserRoutingStrategyUpdate(
                routing_strategy=RoutingStrategy.BEDROCK_ONLY.value
            ),
            session=None,
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_user_routing_strategy_allows_bedrock_only_with_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    key_id = uuid4()

    class FakeUserRepository:
        def __init__(self, _session) -> None:
            self.user = User(
                id=user_id,
                name="user",
                description=None,
                status=UserStatus.ACTIVE,
                monthly_budget_usd=Decimal("10.00"),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

        async def get_by_id(self, _user_id):
            return self.user

        async def update_routing_strategy(self, _user_id, strategy):
            self.user = User(
                id=self.user.id,
                name=self.user.name,
                description=self.user.description,
                status=self.user.status,
                routing_strategy=strategy,
                monthly_budget_usd=self.user.monthly_budget_usd,
                created_at=self.user.created_at,
                updated_at=self.user.updated_at,
            )
            return True

    class FakeAccessKeyRepository:
        def __init__(self, _session) -> None:
            self._keys = [
                AccessKey(
                    id=key_id,
                    user_id=user_id,
                    key_hash="hash",
                    key_prefix="ak",
                    status=KeyStatus.ACTIVE,
                    bedrock_region="ap-northeast-2",
                    bedrock_model="anthropic.claude-sonnet-4-5-20250514",
                    created_at=datetime.now(timezone.utc),
                )
            ]

        async def list_by_user(self, _user_id):
            return self._keys

    class FakeBedrockKeyRepository:
        def __init__(self, _session) -> None:
            return None

        async def list_access_key_ids(self, _access_key_ids):
            return {key_id}

    monkeypatch.setattr(admin_users, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(admin_users, "AccessKeyRepository", FakeAccessKeyRepository)
    monkeypatch.setattr(admin_users, "BedrockKeyRepository", FakeBedrockKeyRepository)

    response = await admin_users.update_user_routing_strategy(
        user_id=user_id,
        data=UserRoutingStrategyUpdate(
            routing_strategy=RoutingStrategy.BEDROCK_ONLY.value
        ),
        session=None,
    )

    assert response.routing_strategy == RoutingStrategy.BEDROCK_ONLY.value
