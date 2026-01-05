from datetime import date
from decimal import Decimal

import pytest

from domain import CostBreakdown, CostCalculator, ModelPricing


def _pricing_fixture(
    input_price: str = "1.00",
    output_price: str = "2.00",
    cache_write_price: str = "3.00",
    cache_read_price: str = "4.00",
) -> ModelPricing:
    return ModelPricing(
        model_id="claude-opus-4-5",
        region="ap-northeast-2",
        input_price_per_million=Decimal(input_price),
        output_price_per_million=Decimal(output_price),
        cache_write_price_per_million=Decimal(cache_write_price),
        cache_read_price_per_million=Decimal(cache_read_price),
        effective_date=date(2025, 1, 1),
    )


# Feature: cost-visibility, Property 2: Cost Calculation Formula Correctness
@pytest.mark.parametrize(
    "tokens, price_per_million, expected",
    [
        (0, "5.00", "0.000000"),
        (1, "1.00", "0.000001"),
        (1, "0.50", "0.000001"),
        (1, "0.40", "0.000000"),
        (250_000, "1.00", "0.250000"),
        (1_234_567, "2.00", "2.469134"),
        (-10, "3.00", "0.000000"),
    ],
)
def test_calculate_token_cost_formula(tokens: int, price_per_million: str, expected: str) -> None:
    cost = CostCalculator._calculate_token_cost(tokens, Decimal(price_per_million))

    assert cost == Decimal(expected)


# Feature: cost-visibility, Property 3: Cost Aggregation Correctness
def test_calculate_cost_aggregation() -> None:
    pricing = _pricing_fixture()

    breakdown = CostCalculator.calculate_cost(
        input_tokens=1_000_000,
        output_tokens=500_000,
        cache_write_tokens=0,
        cache_read_tokens=250_000,
        pricing=pricing,
    )

    assert breakdown.input_cost == Decimal("1.000000")
    assert breakdown.output_cost == Decimal("1.000000")
    assert breakdown.cache_write_cost == Decimal("0.000000")
    assert breakdown.cache_read_cost == Decimal("1.000000")
    assert breakdown.total_cost == Decimal("3.000000")


def test_calculate_cost_zero_tokens() -> None:
    pricing = _pricing_fixture()

    breakdown = CostCalculator.calculate_cost(
        input_tokens=0,
        output_tokens=0,
        cache_write_tokens=0,
        cache_read_tokens=0,
        pricing=pricing,
    )

    assert breakdown == CostBreakdown(
        input_cost=Decimal("0.000000"),
        output_cost=Decimal("0.000000"),
        cache_write_cost=Decimal("0.000000"),
        cache_read_cost=Decimal("0.000000"),
        total_cost=Decimal("0.000000"),
    )


def test_to_dict_preserves_string_precision() -> None:
    breakdown = CostBreakdown(
        input_cost=Decimal("0.123456"),
        output_cost=Decimal("1.000000"),
        cache_write_cost=Decimal("2.500000"),
        cache_read_cost=Decimal("0.000001"),
        total_cost=Decimal("3.623457"),
    )

    payload = breakdown.to_dict()

    assert payload == {
        "input_cost": "0.123456",
        "output_cost": "1.000000",
        "cache_write_cost": "2.500000",
        "cache_read_cost": "0.000001",
        "total_cost": "3.623457",
    }


def test_zero_cost_helper() -> None:
    breakdown = CostCalculator.zero_cost()

    assert breakdown == CostBreakdown(
        input_cost=Decimal("0.000000"),
        output_cost=Decimal("0.000000"),
        cache_write_cost=Decimal("0.000000"),
        cache_read_cost=Decimal("0.000000"),
        total_cost=Decimal("0.000000"),
    )
