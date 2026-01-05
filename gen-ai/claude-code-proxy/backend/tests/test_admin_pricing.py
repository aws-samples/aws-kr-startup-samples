import json
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.api import admin_pricing
from src.domain.pricing import PricingConfig


# Feature: cost-visibility, Property 6: Pricing API Response Completeness
@pytest.mark.asyncio
async def test_get_model_pricing_default_region(monkeypatch: pytest.MonkeyPatch) -> None:
    PricingConfig.reload()

    response = await admin_pricing.get_model_pricing(region="ap-northeast-2")

    assert response.region == "ap-northeast-2"
    model_ids = {model.model_id for model in response.models}
    assert model_ids == {"claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"}


@pytest.mark.asyncio
async def test_get_model_pricing_respects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "ap-northeast-2": {
            "claude-opus-4-5": {
                "input_price_per_million": "9.00",
                "output_price_per_million": "19.00",
                "cache_write_price_per_million": "2.00",
                "cache_read_price_per_million": "0.90",
                "effective_date": "2026-02-01",
            }
        }
    }
    monkeypatch.setenv("PROXY_MODEL_PRICING", json.dumps(payload))
    PricingConfig.reload()

    response = await admin_pricing.get_model_pricing(region="ap-northeast-2")

    model = response.models[0]
    assert model.model_id == "claude-opus-4-5"
    assert model.input_price == "9.00"
    assert model.effective_date == "2026-02-01"


@pytest.mark.asyncio
async def test_reload_pricing_calls_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def _reload() -> None:
        called["value"] = True

    monkeypatch.setattr(PricingConfig, "reload", _reload)

    await admin_pricing.reload_pricing()

    assert called["value"] is True
