import pytest

from src.api import admin_pricing
from src.domain.pricing import PricingConfig


@pytest.mark.asyncio
async def test_get_model_pricing_default_region() -> None:
    PricingConfig.reload()

    response = await admin_pricing.get_model_pricing(region="ap-northeast-2")

    assert response.region == "ap-northeast-2"
    model_ids = {model.model_id for model in response.models}
    assert model_ids == {
        "global.anthropic.claude-opus-4-6-v1",
        "global.anthropic.claude-sonnet-4-6",
        "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    }
    price_by_model = {model.model_id: model.cache_write_1h_price for model in response.models}
    assert price_by_model["global.anthropic.claude-opus-4-6-v1"] == "10.00"
    assert price_by_model["global.anthropic.claude-sonnet-4-6"] == "6.00"
    assert price_by_model["global.anthropic.claude-haiku-4-5-20251001-v1:0"] == "2.00"


@pytest.mark.asyncio
async def test_reload_pricing_calls_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def _reload() -> None:
        called["value"] = True

    monkeypatch.setattr(PricingConfig, "reload", _reload)

    await admin_pricing.reload_pricing()

    assert called["value"] is True
