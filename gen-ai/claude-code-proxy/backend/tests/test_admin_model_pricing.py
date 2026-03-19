from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api import admin_model_pricing
from src.domain import ModelPricingCatalogCreate


@pytest.mark.asyncio
async def test_create_model_pricing_creates_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    pricing_id = uuid4()
    row = SimpleNamespace(
        id=pricing_id,
        provider="bedrock",
        region="ap-northeast-2",
        model_id="global.anthropic.claude-sonnet-4-6",
        input_price_per_million=Decimal("3.00"),
        output_price_per_million=Decimal("15.00"),
        cache_write_price_per_million=Decimal("3.75"),
        cache_write_1h_price_per_million=Decimal("6.00"),
        cache_read_price_per_million=Decimal("0.30"),
        effective_date=date(2025, 1, 1),
        is_active=True,
        updated_at=datetime.now(timezone.utc),
    )

    class FakeModelPricingCatalogRepository:
        def __init__(self, _session) -> None:
            return None

        async def get_by_lookup(self, **_kwargs):
            return None

        async def create(self, **_kwargs):
            return row

        async def list_all(self, include_inactive=False):
            return [row]

    monkeypatch.setattr(
        admin_model_pricing,
        "ModelPricingCatalogRepository",
        FakeModelPricingCatalogRepository,
    )

    class DummySession:
        async def commit(self):
            return None

    response = await admin_model_pricing.create_model_pricing(
        ModelPricingCatalogCreate(
            provider="bedrock",
            region="ap-northeast-2",
            model_id="global.anthropic.claude-sonnet-4-6",
            input_price_per_million=Decimal("3.00"),
            output_price_per_million=Decimal("15.00"),
            cache_write_price_per_million=Decimal("3.75"),
            cache_write_1h_price_per_million=Decimal("6.00"),
            cache_read_price_per_million=Decimal("0.30"),
            effective_date="2025-01-01",
        ),
        session=DummySession(),
    )

    assert response.model_id == "global.anthropic.claude-sonnet-4-6"
    assert response.cache_write_1h_price_per_million == "6.00"


@pytest.mark.asyncio
async def test_delete_model_pricing_blocks_slot_references(monkeypatch: pytest.MonkeyPatch) -> None:
    pricing_id = uuid4()
    pricing_row = SimpleNamespace(
        id=pricing_id,
        provider="bedrock",
        region="ap-northeast-2",
        model_id="global.anthropic.claude-sonnet-4-6",
    )
    slot_row = SimpleNamespace(bedrock_model_id="global.anthropic.claude-sonnet-4-6")

    class FakeModelPricingCatalogRepository:
        def __init__(self, _session) -> None:
            return None

        async def get_by_id(self, _pricing_id):
            return pricing_row

    class FakeModelSlotRepository:
        def __init__(self, _session) -> None:
            return None

        async def list_all(self):
            return [slot_row]

    monkeypatch.setattr(
        admin_model_pricing,
        "ModelPricingCatalogRepository",
        FakeModelPricingCatalogRepository,
    )
    monkeypatch.setattr(admin_model_pricing, "ModelSlotRepository", FakeModelSlotRepository)

    with pytest.raises(HTTPException) as exc:
        await admin_model_pricing.delete_model_pricing(pricing_id, session=None)

    assert exc.value.status_code == 409
