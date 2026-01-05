"""Cost calculator for token usage.

This module calculates estimated costs based on token usage and model pricing,
maintaining 6 decimal precision for accurate cost tracking.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .pricing import ModelPricing


@dataclass
class CostBreakdown:
    """Detailed cost breakdown by token type.
    
    All costs are in USD with 6 decimal precision.
    """
    input_cost: Decimal
    output_cost: Decimal
    cache_write_cost: Decimal
    cache_read_cost: Decimal
    total_cost: Decimal
    
    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary with string values for JSON serialization.
        
        Returns:
            Dictionary with cost values as strings to preserve precision
        """
        return {
            "input_cost": str(self.input_cost),
            "output_cost": str(self.output_cost),
            "cache_write_cost": str(self.cache_write_cost),
            "cache_read_cost": str(self.cache_read_cost),
            "total_cost": str(self.total_cost),
        }


class CostCalculator:
    """Calculates estimated costs based on token usage and model pricing.
    
    Uses the formula: cost = (tokens / 1,000,000) * price_per_million
    All calculations maintain 6 decimal precision with ROUND_HALF_UP rounding.
    """
    
    PRECISION = Decimal("0.000001")  # 6 decimal places
    TOKENS_PER_MILLION = Decimal("1000000")
    
    @classmethod
    def calculate_cost(
        cls,
        input_tokens: int,
        output_tokens: int,
        cache_write_tokens: int,
        cache_read_tokens: int,
        pricing: ModelPricing,
    ) -> CostBreakdown:
        """Calculate cost breakdown for given token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cache_write_tokens: Number of cache write tokens
            cache_read_tokens: Number of cache read tokens
            pricing: ModelPricing with unit prices
            
        Returns:
            CostBreakdown with individual and total costs
        """
        input_cost = cls._calculate_token_cost(
            input_tokens, pricing.input_price_per_million
        )
        output_cost = cls._calculate_token_cost(
            output_tokens, pricing.output_price_per_million
        )
        cache_write_cost = cls._calculate_token_cost(
            cache_write_tokens, pricing.cache_write_price_per_million
        )
        cache_read_cost = cls._calculate_token_cost(
            cache_read_tokens, pricing.cache_read_price_per_million
        )
        
        total_cost = (
            input_cost + output_cost + cache_write_cost + cache_read_cost
        ).quantize(cls.PRECISION, rounding=ROUND_HALF_UP)
        
        return CostBreakdown(
            input_cost=input_cost,
            output_cost=output_cost,
            cache_write_cost=cache_write_cost,
            cache_read_cost=cache_read_cost,
            total_cost=total_cost,
        )
    
    @classmethod
    def _calculate_token_cost(cls, tokens: int, price_per_million: Decimal) -> Decimal:
        """Calculate cost for a specific token type.
        
        Args:
            tokens: Number of tokens
            price_per_million: Price per 1 million tokens in USD
            
        Returns:
            Cost in USD with 6 decimal precision
        """
        if tokens <= 0:
            return Decimal("0.000000")
        
        cost = (Decimal(tokens) / cls.TOKENS_PER_MILLION) * price_per_million
        return cost.quantize(cls.PRECISION, rounding=ROUND_HALF_UP)
    
    @classmethod
    def zero_cost(cls) -> CostBreakdown:
        """Return a zero-cost breakdown for error cases.
        
        Returns:
            CostBreakdown with all costs set to 0
        """
        zero = Decimal("0.000000")
        return CostBreakdown(
            input_cost=zero,
            output_cost=zero,
            cache_write_cost=zero,
            cache_read_cost=zero,
            total_cost=zero,
        )
