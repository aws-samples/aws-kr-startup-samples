import json
from datetime import date
from decimal import Decimal

import pytest

from domain import PricingConfig


@pytest.fixture(autouse=True)
def reset_pricing_config(monkeypatch: pytest.MonkeyPatch) -> None:
    PricingConfig._initialized = False
    PricingConfig._PRICING_DATA.clear()
    monkeypatch.delenv("PROXY_MODEL_PRICING", raising=False)
    yield
    PricingConfig._initialized = False
    PricingConfig._PRICING_DATA.clear()


# Feature: cost-visibility, Property 1: Model Pricing Storage and Retrieval
@pytest.mark.parametrize(
    "model_id",
    [
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
    ],
)
def test_default_pricing_returns_positive_values(model_id: str) -> None:
    pricing = PricingConfig.get_pricing(model_id)

    assert pricing is not None
    assert pricing.region == "ap-northeast-2"
    assert pricing.input_price_per_million > 0
    assert pricing.output_price_per_million > 0
    assert pricing.cache_write_price_per_million > 0
    assert pricing.cache_read_price_per_million > 0
    assert pricing.effective_date == date(2025, 1, 1)


def test_get_all_pricing_returns_expected_models() -> None:
    pricing_list = PricingConfig.get_all_pricing()
    model_ids = {pricing.model_id for pricing in pricing_list}

    assert model_ids == {
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
    }


def test_get_pricing_falls_back_to_default_region() -> None:
    pricing = PricingConfig.get_pricing("claude-opus-4-5", region="eu-west-1")

    assert pricing is not None
    assert pricing.region == "ap-northeast-2"


def test_reload_picks_up_env_pricing(monkeypatch: pytest.MonkeyPatch) -> None:
    pricing_payload = {
        "ap-northeast-2": {
            "claude-opus-4-5": {
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
    pricing = PricingConfig.get_pricing("claude-opus-4-5")

    assert pricing is not None
    assert pricing.input_price_per_million == Decimal("7.00")
    assert pricing.output_price_per_million == Decimal("21.00")
    assert pricing.cache_write_price_per_million == Decimal("6.00")
    assert pricing.cache_read_price_per_million == Decimal("0.60")
    assert pricing.effective_date == date(2026, 1, 1)


def test_reload_updates_after_env_change(monkeypatch: pytest.MonkeyPatch) -> None:
    first_payload = {
        "ap-northeast-2": {
            "claude-haiku-4-5": {
                "input_price_per_million": "1.10",
                "output_price_per_million": "5.10",
                "cache_write_price_per_million": "1.30",
                "cache_read_price_per_million": "0.11",
                "effective_date": "2025-02-01",
            }
        }
    }
    monkeypatch.setenv("PROXY_MODEL_PRICING", json.dumps(first_payload))
    PricingConfig.reload()

    first_pricing = PricingConfig.get_pricing("claude-haiku-4-5")
    assert first_pricing is not None
    assert first_pricing.input_price_per_million == Decimal("1.10")

    second_payload = {
        "ap-northeast-2": {
            "claude-haiku-4-5": {
                "input_price_per_million": "1.25",
                "output_price_per_million": "5.25",
                "cache_write_price_per_million": "1.35",
                "cache_read_price_per_million": "0.12",
                "effective_date": "2025-03-01",
            }
        }
    }
    monkeypatch.setenv("PROXY_MODEL_PRICING", json.dumps(second_payload))
    PricingConfig.reload()

    second_pricing = PricingConfig.get_pricing("claude-haiku-4-5")
    assert second_pricing is not None
    assert second_pricing.input_price_per_million == Decimal("1.25")
    assert second_pricing.effective_date == date(2025, 3, 1)


def test_reload_missing_fields_falls_back_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    pricing_payload = {
        "ap-northeast-2": {
            "claude-opus-4-5": {
                "input_price_per_million": "7.00",
            }
        }
    }
    monkeypatch.setenv("PROXY_MODEL_PRICING", json.dumps(pricing_payload))

    PricingConfig.reload()
    pricing = PricingConfig.get_pricing("claude-opus-4-5")

    assert pricing is not None
    assert pricing.input_price_per_million == Decimal("5.00")
    assert pricing.output_price_per_million == Decimal("25.00")


def test_invalid_env_json_falls_back_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROXY_MODEL_PRICING", "{")

    PricingConfig.reload()
    pricing = PricingConfig.get_pricing("claude-opus-4-5")

    assert pricing is not None
    assert pricing.input_price_per_million == Decimal("5.00")
    assert pricing.output_price_per_million == Decimal("25.00")


def test_get_all_pricing_falls_back_to_default_region() -> None:
    pricing_list = PricingConfig.get_all_pricing(region="eu-west-1")
    regions = {pricing.region for pricing in pricing_list}

    assert regions == {"ap-northeast-2"}


# Feature: cost-visibility, Property 7: Model ID Normalization Consistency
@pytest.mark.parametrize(
    "raw_model_id, expected",
    [
        ("anthropic.claude-sonnet-4-5-20250514", "claude-sonnet-4-5"),
        ("global.anthropic.claude-opus-4-5-20250514", "claude-opus-4-5"),
        ("anthropic.claude-haiku-4.5-20250514", "claude-haiku-4-5"),
        ("claude-opus-4-5", "claude-opus-4-5"),
        ("unknown-model", "unknown-model"),
    ],
)
def test_normalize_model_id_variants(raw_model_id: str, expected: str) -> None:
    assert PricingConfig.normalize_model_id(raw_model_id) == expected
