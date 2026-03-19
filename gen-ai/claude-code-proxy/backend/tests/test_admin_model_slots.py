from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.api import admin_model_slots
from src.domain import ModelSlotUpdate


@pytest.mark.asyncio
async def test_list_model_slots_returns_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    row = SimpleNamespace(
        id=uuid4(),
        slot="sonnet",
        bedrock_model_id="global.anthropic.claude-sonnet-4-6",
        description=None,
        updated_at=datetime.now(timezone.utc),
    )

    class FakeModelSlotRepository:
        def __init__(self, _session) -> None:
            return None

        async def list_all(self):
            return [row]

    monkeypatch.setattr(admin_model_slots, "ModelSlotRepository", FakeModelSlotRepository)

    response = await admin_model_slots.list_model_slots(session=None)

    assert len(response) == 1
    assert response[0].slot == "sonnet"


@pytest.mark.asyncio
async def test_update_model_slot_updates_existing_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    slot_id = uuid4()
    row = SimpleNamespace(
        id=slot_id,
        slot="opus",
        bedrock_model_id="global.anthropic.claude-opus-4-6-v1",
        description=None,
        updated_at=datetime.now(timezone.utc),
    )

    class FakeModelSlotRepository:
        def __init__(self, _session) -> None:
            return None

        async def get_by_slot(self, _slot):
            return row

        async def update_slot(self, _slot, *, bedrock_model_id, description=None):
            row.bedrock_model_id = bedrock_model_id
            row.description = description
            return row

        async def get_slot_mapping(self):
            return {"opus": row.bedrock_model_id}

    monkeypatch.setattr(admin_model_slots, "ModelSlotRepository", FakeModelSlotRepository)

    class DummySession:
        async def commit(self):
            return None

    response = await admin_model_slots.update_model_slot(
        "opus",
        ModelSlotUpdate(bedrock_model_id="new-opus"),
        session=DummySession(),
    )

    assert response.bedrock_model_id == "new-opus"
