import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domain import PricingConfig


@pytest.fixture(autouse=True)
def reset_pricing_config(monkeypatch: pytest.MonkeyPatch) -> None:
    PricingConfig._initialized = False
    PricingConfig._PRICING_DATA.clear()
    PricingConfig._CATALOG_DATA = None
    monkeypatch.delenv("PROXY_MODEL_PRICING", raising=False)
    monkeypatch.delenv("PROXY_PLAN_PRICING", raising=False)
    yield
    PricingConfig._initialized = False
    PricingConfig._PRICING_DATA.clear()
    PricingConfig._CATALOG_DATA = None


@pytest.mark.parametrize(
    "provider, model_id",
    [
        ("bedrock", "global.anthropic.claude-opus-4-6-v1"),
        ("bedrock", "global.anthropic.claude-sonnet-4-6"),
        ("bedrock", "global.anthropic.claude-haiku-4-5-20251001-v1:0"),
        ("plan", "claude-opus-4-6-v1"),
        ("plan", "claude-sonnet-4-6"),
        ("plan", "claude-haiku-4-5-20251001"),
    ],
)
def test_default_pricing_returns_positive_values(provider: str, model_id: str) -> None:
    pricing = PricingConfig.get_pricing(
        model_id,
        region="global" if provider == "plan" else "ap-northeast-2",
        provider=provider,
    )

    assert pricing is not None
    assert pricing.input_price_per_million > 0
    assert pricing.output_price_per_million > 0
    assert pricing.cache_write_price_per_million > 0
    assert pricing.cache_read_price_per_million > 0
    assert pricing.effective_date == date(2025, 1, 1)


def test_get_all_pricing_returns_exact_model_ids() -> None:
    pricing_list = PricingConfig.get_all_pricing(provider="bedrock")
    model_ids = {pricing.model_id for pricing in pricing_list}

    assert model_ids == {
        "global.anthropic.claude-opus-4-6-v1",
        "global.anthropic.claude-sonnet-4-6",
        "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    }


def test_get_pricing_falls_back_to_default_region() -> None:
    pricing = PricingConfig.get_pricing(
        "global.anthropic.claude-opus-4-6-v1", region="eu-west-1", provider="bedrock"
    )

    assert pricing is not None
    assert pricing.region == "ap-northeast-2"


def test_reload_picks_up_env_pricing(monkeypatch: pytest.MonkeyPatch) -> None:
    pricing_payload = {
        "ap-northeast-2": {
            "global.anthropic.claude-opus-4-6-v1": {
                "input_price_per_million": "7.00",
                "output_price_per_million": "21.00",
                "cache_write_price_per_million": "6.00",
                "cache_read_price_per_million": "0.60",
                "effective_date": "2026-01-01",
            }
        }
    }
    monkeypatch.setenv("PROXY_MODEL_PRICING", json.dumps(pricing_payload))

    PricingConfig.reload()
    pricing = PricingConfig.get_pricing("global.anthropic.claude-opus-4-6-v1", provider="bedrock")

    assert pricing is not None
    assert pricing.input_price_per_million == Decimal("7.00")
    assert pricing.output_price_per_million == Decimal("21.00")


def test_family_aliases_still_resolve_to_exact_entries() -> None:
    pricing = PricingConfig.get_pricing("claude-sonnet-4-6", provider="bedrock")

    assert pricing is not None
    assert pricing.model_id == "global.anthropic.claude-sonnet-4-6"


def test_one_hour_cache_write_prices_are_available_for_supported_models() -> None:
    pricing = PricingConfig.get_pricing("global.anthropic.claude-opus-4-6-v1", provider="bedrock")

    assert pricing is not None
    assert pricing.cache_write_1h_price_per_million == Decimal("10.00")

    resolved = pricing.resolve_for_usage(caching_strategy="1h")
    assert resolved.cache_write_price_per_million == Decimal("10.00")


def test_catalog_pricing_overrides_defaults() -> None:
    entries = [
        SimpleNamespace(
            provider="bedrock",
            region="ap-northeast-2",
            model_id="global.anthropic.claude-sonnet-4-6",
            input_price_per_million=Decimal("8.00"),
            output_price_per_million=Decimal("18.00"),
            cache_write_price_per_million=Decimal("2.00"),
            cache_read_price_per_million=Decimal("0.20"),
            effective_date=date(2026, 3, 1),
        )
    ]

    PricingConfig.set_catalog_pricing(PricingConfig.build_pricing_data_from_entries(entries))
    pricing = PricingConfig.get_pricing("global.anthropic.claude-sonnet-4-6", provider="bedrock")

    assert pricing is not None
    assert pricing.input_price_per_million == Decimal("8.00")
    assert pricing.effective_date == date(2026, 3, 1)
