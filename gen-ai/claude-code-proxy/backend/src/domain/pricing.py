"""Model pricing configuration for cost visibility.

This module manages pricing information for Claude 4.5 models (Opus, Sonnet, Haiku)
with support for runtime configuration updates via environment variables.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict
import json
import os


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


class PricingConfig:
    """Configuration for model pricing by region.
    
    Supports runtime updates via PROXY_MODEL_PRICING environment variable
    or by calling reload() after updating the environment.
    """
    
    _PRICING_DATA: Dict[str, Dict[str, ModelPricing]] = {}
    _initialized: bool = False
    
    # Known Bedrock model ID patterns for normalization
    _MODEL_MAPPINGS: Dict[str, str] = {
        "anthropic.claude-opus-4-5": "claude-opus-4-5",
        "anthropic.claude-sonnet-4-5": "claude-sonnet-4-5",
        "anthropic.claude-haiku-4-5": "claude-haiku-4-5",
        "global.anthropic.claude-opus-4-5": "claude-opus-4-5",
        "global.anthropic.claude-sonnet-4-5": "claude-sonnet-4-5",
        "global.anthropic.claude-haiku-4-5": "claude-haiku-4-5",
    }
    
    @classmethod
    def _initialize(cls) -> None:
        """Initialize pricing from environment or defaults."""
        if cls._initialized:
            return
        
        # Try to load from environment variable (JSON string)
        pricing_json = os.environ.get("PROXY_MODEL_PRICING")
        if pricing_json:
            try:
                cls._load_from_json(pricing_json)
                cls._initialized = True
                return
            except Exception:
                # Fallback to defaults on invalid config
                pass
        
        cls._load_defaults()
        cls._initialized = True
    
    @classmethod
    def _load_defaults(cls) -> None:
        """Load default pricing for ap-northeast-2 (Seoul) region."""
        default_region = "ap-northeast-2"
        effective_date = date(2025, 1, 1)
        
        cls._PRICING_DATA[default_region] = {
            "claude-opus-4-5": ModelPricing(
                model_id="claude-opus-4-5",
                region=default_region,
                input_price_per_million=Decimal("5.00"),
                output_price_per_million=Decimal("25.00"),
                cache_write_price_per_million=Decimal("6.25"),
                cache_read_price_per_million=Decimal("0.50"),
                effective_date=effective_date,
            ),
            "claude-sonnet-4-5": ModelPricing(
                model_id="claude-sonnet-4-5",
                region=default_region,
                input_price_per_million=Decimal("3.00"),
                output_price_per_million=Decimal("15.00"),
                cache_write_price_per_million=Decimal("3.75"),
                cache_read_price_per_million=Decimal("0.30"),
                effective_date=effective_date,
            ),
            "claude-haiku-4-5": ModelPricing(
                model_id="claude-haiku-4-5",
                region=default_region,
                input_price_per_million=Decimal("1.00"),
                output_price_per_million=Decimal("5.00"),
                cache_write_price_per_million=Decimal("1.25"),
                cache_read_price_per_million=Decimal("0.10"),
                effective_date=effective_date,
            ),
        }

    @classmethod
    def _load_from_json(cls, pricing_json: str) -> None:
        """Load pricing from JSON string in PROXY_MODEL_PRICING.
        
        Expected format:
        {
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
        """
        data = json.loads(pricing_json)
        cls._PRICING_DATA.clear()
        
        for region, models in data.items():
            cls._PRICING_DATA[region] = {}
            for model_id, prices in models.items():
                effective_date_str = prices.get("effective_date", "1970-01-01")
                cls._PRICING_DATA[region][model_id] = ModelPricing(
                    model_id=model_id,
                    region=region,
                    input_price_per_million=Decimal(str(prices["input_price_per_million"])),
                    output_price_per_million=Decimal(str(prices["output_price_per_million"])),
                    cache_write_price_per_million=Decimal(str(prices["cache_write_price_per_million"])),
                    cache_read_price_per_million=Decimal(str(prices["cache_read_price_per_million"])),
                    effective_date=date.fromisoformat(effective_date_str),
                )
    
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
    def get_pricing(cls, model_id: str, region: str = "ap-northeast-2") -> ModelPricing | None:
        """Get pricing for a model in a specific region.
        
        Args:
            model_id: Bedrock model ID (will be normalized) or pricing key
            region: AWS region code (defaults to ap-northeast-2)
            
        Returns:
            ModelPricing if found, None otherwise
        """
        cls._initialize()
        normalized_id = cls._normalize_model_id(model_id)
        
        # Try requested region first, fall back to default
        region_pricing = cls._PRICING_DATA.get(region)
        if region_pricing is None:
            region_pricing = cls._PRICING_DATA.get("ap-northeast-2", {})
        
        return region_pricing.get(normalized_id)
    
    @classmethod
    def get_all_pricing(cls, region: str = "ap-northeast-2") -> list[ModelPricing]:
        """Get pricing for all configured models in a region.
        
        Args:
            region: AWS region code (defaults to ap-northeast-2)
            
        Returns:
            List of ModelPricing for all models in the region
        """
        cls._initialize()
        region_pricing = cls._PRICING_DATA.get(region)
        if region_pricing is None:
            region_pricing = cls._PRICING_DATA.get("ap-northeast-2", {})
        
        return list(region_pricing.values())

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
        # Handle both "4-5" and "4.5" formats
        normalized_version = model_lower.replace("4.5", "4-5")
        
        if "opus" in normalized_version and "4-5" in normalized_version:
            return "claude-opus-4-5"
        elif "sonnet" in normalized_version and "4-5" in normalized_version:
            return "claude-sonnet-4-5"
        elif "haiku" in normalized_version and "4-5" in normalized_version:
            return "claude-haiku-4-5"
        
        # Return as-is if no match found
        return model_id
