"""Model pricing configuration for cost visibility.

This module manages pricing information for Claude 4.5/4.6 models (Opus, Sonnet, Haiku)
with support for runtime configuration updates via environment variables.
"""

import json
import os
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Dict, Iterable

from .types import Provider


@dataclass(frozen=True)
class ModelPricing:
    """Pricing information for a single model.

    All prices are in USD per 1 million tokens.
    """

    model_id: str
    region: str
    input_price_per_million: Decimal
    output_price_per_million: Decimal
    cache_write_price_per_million: Decimal
    cache_read_price_per_million: Decimal
    effective_date: date
    cache_write_1h_price_per_million: Decimal | None = None

    def resolve_for_usage(self, *, caching_strategy: str | None) -> "ModelPricing":
        if caching_strategy != "1h" or self.cache_write_1h_price_per_million is None:
            return self
        return replace(
            self,
            cache_write_price_per_million=self.cache_write_1h_price_per_million,
        )


class PricingConfig:
    """Configuration for model pricing by provider and region.

    Supports runtime updates via PROXY_MODEL_PRICING or PROXY_PLAN_PRICING
    environment variables or by calling reload() after updating the environment.
    """

    _PRICING_DATA: Dict[str, Dict[str, Dict[str, ModelPricing]]] = {}
    _initialized: bool = False
    _CATALOG_DATA: Dict[str, Dict[str, Dict[str, ModelPricing]]] | None = None

    # Known Bedrock model ID patterns for normalization
    _MODEL_MAPPINGS: Dict[str, str] = {
        "anthropic.claude-opus-4-5": "claude-opus-4-5",
        "anthropic.claude-opus-4-6": "claude-opus-4-6",
        "anthropic.claude-sonnet-4-5": "claude-sonnet-4-5",
        "anthropic.claude-sonnet-4-6": "claude-sonnet-4-6",
        "anthropic.claude-haiku-4-5": "claude-haiku-4-5",
        "global.anthropic.claude-opus-4-5": "claude-opus-4-5",
        "global.anthropic.claude-opus-4-6": "claude-opus-4-6",
        "global.anthropic.claude-sonnet-4-5": "claude-sonnet-4-5",
        "global.anthropic.claude-sonnet-4-6": "claude-sonnet-4-6",
        "global.anthropic.claude-haiku-4-5": "claude-haiku-4-5",
    }
    _FAMILY_ALIAS_TO_MODEL_ID: Dict[str, Dict[str, str]] = {
        "bedrock": {
            "claude-opus-4-6": "global.anthropic.claude-opus-4-6-v1",
            "claude-sonnet-4-6": "global.anthropic.claude-sonnet-4-6",
            "claude-haiku-4-5": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        },
        "plan": {
            "claude-opus-4-6": "claude-opus-4-6-v1",
            "claude-sonnet-4-6": "claude-sonnet-4-6",
            "claude-haiku-4-5": "claude-haiku-4-5-20251001",
        },
    }

    @classmethod
    def _initialize(cls) -> None:
        """Initialize pricing from environment or defaults."""
        if cls._initialized:
            return

        cls._load_defaults()

        if cls._CATALOG_DATA:
            cls._merge_pricing_data(cls._CATALOG_DATA)
            cls._initialized = True
            return

        model_pricing_json = os.environ.get("PROXY_MODEL_PRICING")
        plan_pricing_json = os.environ.get("PROXY_PLAN_PRICING")
        if model_pricing_json or plan_pricing_json:
            try:
                if model_pricing_json:
                    cls._load_from_json(model_pricing_json, merge=True)
                if plan_pricing_json:
                    cls._load_from_json(plan_pricing_json, default_provider="plan", merge=True)
                cls._initialized = True
                return
            except Exception:
                cls._PRICING_DATA.clear()
                cls._load_defaults()

        cls._initialized = True

    @classmethod
    def set_catalog_pricing(
        cls, pricing_data: Dict[str, Dict[str, Dict[str, ModelPricing]]]
    ) -> None:
        cls._CATALOG_DATA = pricing_data
        cls.reload()

    @classmethod
    def clear_catalog_pricing(cls) -> None:
        cls._CATALOG_DATA = None
        cls.reload()

    @classmethod
    def _merge_pricing_data(
        cls, pricing_data: Dict[str, Dict[str, Dict[str, ModelPricing]]]
    ) -> None:
        for provider, regions in pricing_data.items():
            provider_bucket = cls._PRICING_DATA.setdefault(provider, {})
            for region, models in regions.items():
                region_bucket = provider_bucket.setdefault(region, {})
                region_bucket.update(models)

    @classmethod
    def build_pricing_data_from_entries(
        cls, entries: Iterable[object]
    ) -> Dict[str, Dict[str, Dict[str, ModelPricing]]]:
        pricing_data: Dict[str, Dict[str, Dict[str, ModelPricing]]] = {}
        for entry in entries:
            provider_bucket = pricing_data.setdefault(str(entry.provider), {})
            region_bucket = provider_bucket.setdefault(str(entry.region), {})
            region_bucket[str(entry.model_id)] = ModelPricing(
                model_id=str(entry.model_id),
                region=str(entry.region),
                input_price_per_million=Decimal(str(entry.input_price_per_million)),
                output_price_per_million=Decimal(str(entry.output_price_per_million)),
                cache_write_price_per_million=Decimal(str(entry.cache_write_price_per_million)),
                cache_read_price_per_million=Decimal(str(entry.cache_read_price_per_million)),
                effective_date=entry.effective_date,
                cache_write_1h_price_per_million=Decimal(
                    str(
                        getattr(
                            entry,
                            "cache_write_1h_price_per_million",
                            entry.cache_write_price_per_million,
                        )
                    )
                ),
            )
        return pricing_data

    @classmethod
    def _load_defaults(cls) -> None:
        """Load default pricing for bedrock and plan providers."""
        default_region = "ap-northeast-2"
        plan_region = "global"
        effective_date = date(2025, 1, 1)

        cls._PRICING_DATA["bedrock"] = {
            default_region: {
                "global.anthropic.claude-opus-4-6-v1": ModelPricing(
                    model_id="global.anthropic.claude-opus-4-6-v1",
                    region=default_region,
                    input_price_per_million=Decimal("5.00"),
                    output_price_per_million=Decimal("25.00"),
                    cache_write_price_per_million=Decimal("6.25"),
                    cache_read_price_per_million=Decimal("0.50"),
                    effective_date=effective_date,
                    cache_write_1h_price_per_million=Decimal("10.00"),
                ),
                "global.anthropic.claude-sonnet-4-6": ModelPricing(
                    model_id="global.anthropic.claude-sonnet-4-6",
                    region=default_region,
                    input_price_per_million=Decimal("3.00"),
                    output_price_per_million=Decimal("15.00"),
                    cache_write_price_per_million=Decimal("3.75"),
                    cache_read_price_per_million=Decimal("0.30"),
                    effective_date=effective_date,
                    cache_write_1h_price_per_million=Decimal("6.00"),
                ),
                "global.anthropic.claude-haiku-4-5-20251001-v1:0": ModelPricing(
                    model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
                    region=default_region,
                    input_price_per_million=Decimal("1.00"),
                    output_price_per_million=Decimal("5.00"),
                    cache_write_price_per_million=Decimal("1.25"),
                    cache_read_price_per_million=Decimal("0.10"),
                    effective_date=effective_date,
                    cache_write_1h_price_per_million=Decimal("2.00"),
                ),
            }
        }

        cls._PRICING_DATA["plan"] = {
            plan_region: {
                "claude-opus-4-6-v1": ModelPricing(
                    model_id="claude-opus-4-6-v1",
                    region=plan_region,
                    input_price_per_million=Decimal("5.00"),
                    output_price_per_million=Decimal("25.00"),
                    cache_write_price_per_million=Decimal("6.25"),
                    cache_read_price_per_million=Decimal("0.50"),
                    effective_date=effective_date,
                    cache_write_1h_price_per_million=Decimal("10.00"),
                ),
                "claude-sonnet-4-6": ModelPricing(
                    model_id="claude-sonnet-4-6",
                    region=plan_region,
                    input_price_per_million=Decimal("3.00"),
                    output_price_per_million=Decimal("15.00"),
                    cache_write_price_per_million=Decimal("3.75"),
                    cache_read_price_per_million=Decimal("0.30"),
                    effective_date=effective_date,
                    cache_write_1h_price_per_million=Decimal("6.00"),
                ),
                "claude-haiku-4-5-20251001": ModelPricing(
                    model_id="claude-haiku-4-5-20251001",
                    region=plan_region,
                    input_price_per_million=Decimal("1.00"),
                    output_price_per_million=Decimal("5.00"),
                    cache_write_price_per_million=Decimal("1.25"),
                    cache_read_price_per_million=Decimal("0.10"),
                    effective_date=effective_date,
                    cache_write_1h_price_per_million=Decimal("2.00"),
                ),
            }
        }

    @classmethod
    def _load_from_json(
        cls,
        pricing_json: str,
        *,
        default_provider: Provider | None = None,
        merge: bool = False,
    ) -> None:
        """Load pricing from JSON string in PROXY_MODEL_PRICING or PROXY_PLAN_PRICING.

        Expected format:
        {
            "bedrock": {
                "ap-northeast-2": {
                    "claude-opus-4-5": {
                        "input_price_per_million": "5.00",
                        "output_price_per_million": "25.00",
                        "cache_write_price_per_million": "6.25",
                        "cache_read_price_per_million": "0.50",
                        "effective_date": "2025-01-01"
                    }
                }
            }
        }
        """
        data = json.loads(pricing_json)
        parsed = cls._parse_pricing_payload(data, default_provider=default_provider)
        if not merge:
            cls._PRICING_DATA.clear()
        cls._merge_pricing_data(parsed)

    @classmethod
    def _parse_pricing_payload(
        cls, data: dict, *, default_provider: Provider | None = None
    ) -> Dict[str, Dict[str, Dict[str, ModelPricing]]]:
        if default_provider:
            provider_data = data
            if isinstance(data, dict) and default_provider in data:
                provider_data = data[default_provider]
            return {
                default_provider: cls._parse_region_models(provider_data, provider=default_provider)
            }

        if any(provider in data for provider in ("bedrock", "plan")):
            providers: Dict[str, Dict[str, Dict[str, ModelPricing]]] = {}
            for provider, provider_data in data.items():
                providers[provider] = cls._parse_region_models(provider_data, provider=provider)
            return providers

        return {"bedrock": cls._parse_region_models(data, provider="bedrock")}

    @classmethod
    def _parse_region_models(
        cls, data: dict, *, provider: Provider
    ) -> Dict[str, Dict[str, ModelPricing]]:
        regions: Dict[str, Dict[str, ModelPricing]] = {}
        for region, models in data.items():
            region_key = region
            if provider == "plan" and (region is None or region == ""):
                region_key = "global"
            regions[str(region_key)] = {}
            for model_id, prices in models.items():
                effective_date_str = prices.get("effective_date", "1970-01-01")
                regions[str(region_key)][model_id] = ModelPricing(
                    model_id=model_id,
                    region=str(region_key),
                    input_price_per_million=Decimal(str(prices["input_price_per_million"])),
                    output_price_per_million=Decimal(str(prices["output_price_per_million"])),
                    cache_write_price_per_million=Decimal(
                        str(prices["cache_write_price_per_million"])
                    ),
                    cache_read_price_per_million=Decimal(
                        str(prices["cache_read_price_per_million"])
                    ),
                    effective_date=date.fromisoformat(effective_date_str),
                    cache_write_1h_price_per_million=Decimal(
                        str(
                            prices.get(
                                "cache_write_1h_price_per_million",
                                prices["cache_write_price_per_million"],
                            )
                        )
                    ),
                )
        return regions

    @classmethod
    def reload(cls) -> None:
        """Force reload pricing configuration from environment.

        Call this after updating PROXY_MODEL_PRICING to apply new prices
        without restarting the application.
        """
        cls._initialized = False
        cls._PRICING_DATA.clear()
        cls._initialize()

    @classmethod
    def get_pricing(
        cls,
        model_id: str,
        region: str = "ap-northeast-2",
        provider: Provider = "bedrock",
    ) -> ModelPricing | None:
        """Get pricing for a model in a specific region.

        Args:
            model_id: Bedrock model ID (will be normalized) or pricing key
            region: AWS region code (defaults to ap-northeast-2)
            provider: Pricing provider ("bedrock" or "plan")

        Returns:
            ModelPricing if found, None otherwise
        """
        cls._initialize()
        normalized_id = cls._normalize_model_id(model_id)
        provider_aliases = cls._FAMILY_ALIAS_TO_MODEL_ID.get(provider, {})
        alias_model_id = provider_aliases.get(normalized_id, normalized_id)

        provider_pricing = cls._PRICING_DATA.get(provider, {})
        region_pricing = provider_pricing.get(region)
        if provider == "plan" and region_pricing is None:
            region_pricing = provider_pricing.get("global", {})
        if provider == "bedrock" and region_pricing is None:
            region_pricing = provider_pricing.get("ap-northeast-2", {})

        if not region_pricing:
            return None
        return (
            region_pricing.get(model_id)
            or region_pricing.get(alias_model_id)
            or region_pricing.get(normalized_id)
        )

    @classmethod
    def get_all_pricing(
        cls, region: str = "ap-northeast-2", provider: Provider = "bedrock"
    ) -> list[ModelPricing]:
        """Get pricing for all configured models in a region.

        Args:
            region: AWS region code (defaults to ap-northeast-2)
            provider: Pricing provider ("bedrock" or "plan")

        Returns:
            List of ModelPricing for all models in the region
        """
        cls._initialize()
        provider_pricing = cls._PRICING_DATA.get(provider, {})
        region_pricing = provider_pricing.get(region)
        if provider == "plan" and region_pricing is None:
            region_pricing = provider_pricing.get("global", {})
        if provider == "bedrock" and region_pricing is None:
            region_pricing = provider_pricing.get("ap-northeast-2", {})

        return list(region_pricing.values()) if region_pricing else []

    @classmethod
    def normalize_model_id(cls, model_id: str) -> str:
        """Public helper for normalized pricing keys.

        Args:
            model_id: Bedrock model ID or pricing key

        Returns:
            Normalized pricing key (e.g., "claude-sonnet-4-5")
        """
        return cls._normalize_model_id(model_id)

    @classmethod
    def _normalize_model_id(cls, model_id: str) -> str:
        """Normalize Bedrock model ID to pricing key.

        Handles various Bedrock model ID formats:
        - anthropic.claude-sonnet-4-5-20250514
        - global.anthropic.claude-opus-4-5-20250514
        - claude-sonnet-4-5 (already normalized)

        Args:
            model_id: Raw model ID from Bedrock API

        Returns:
            Normalized pricing key
        """
        model_lower = model_id.lower()

        # Try exact prefix match first
        for prefix, normalized in cls._MODEL_MAPPINGS.items():
            if model_lower.startswith(prefix):
                return normalized

        # Fallback: check for model family keywords
        # Handle both "4-5"/"4.5" and "4-6"/"4.6" formats
        normalized_version = model_lower.replace("4.5", "4-5")
        normalized_version = normalized_version.replace("4.6", "4-6")

        if "opus" in normalized_version and "4-5" in normalized_version:
            return "claude-opus-4-5"
        elif "opus" in normalized_version and "4-6" in normalized_version:
            return "claude-opus-4-6"
        elif "sonnet" in normalized_version and "4-5" in normalized_version:
            return "claude-sonnet-4-5"
        elif "sonnet" in normalized_version and "4-6" in normalized_version:
            return "claude-sonnet-4-6"
        elif "haiku" in normalized_version and "4-5" in normalized_version:
            return "claude-haiku-4-5"

        # Return as-is if no match found
        return model_id
