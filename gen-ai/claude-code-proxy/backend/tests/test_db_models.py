import sys
from pathlib import Path

from sqlalchemy import BigInteger, Date, Numeric, String

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.db.models import TokenUsageModel, UsageAggregateModel, UserModel


def test_token_usage_model_has_cost_snapshot_columns() -> None:
    columns = TokenUsageModel.__table__.columns
    expected = {
        "estimated_cost_usd",
        "input_cost_usd",
        "output_cost_usd",
        "cache_write_cost_usd",
        "cache_read_cost_usd",
        "pricing_region",
        "pricing_model_id",
        "pricing_effective_date",
        "pricing_input_price_per_million",
        "pricing_output_price_per_million",
        "pricing_cache_write_price_per_million",
        "pricing_cache_read_price_per_million",
    }

    assert expected.issubset(set(columns.keys()))

    assert isinstance(columns["estimated_cost_usd"].type, Numeric)
    assert columns["estimated_cost_usd"].type.precision == 12
    assert columns["estimated_cost_usd"].type.scale == 6

    assert isinstance(columns["pricing_effective_date"].type, Date)

    pricing_region = columns["pricing_region"].type
    assert isinstance(pricing_region, String)
    assert pricing_region.length == 32

    pricing_model_id = columns["pricing_model_id"].type
    assert isinstance(pricing_model_id, String)
    assert pricing_model_id.length == 64


def test_usage_aggregates_model_has_cost_totals() -> None:
    columns = UsageAggregateModel.__table__.columns
    expected = {
        "total_cache_write_tokens",
        "total_cache_read_tokens",
        "total_input_cost_usd",
        "total_output_cost_usd",
        "total_cache_write_cost_usd",
        "total_cache_read_cost_usd",
        "total_estimated_cost_usd",
    }

    assert expected.issubset(set(columns.keys()))

    cache_write_tokens = columns["total_cache_write_tokens"].type
    cache_read_tokens = columns["total_cache_read_tokens"].type
    assert isinstance(cache_write_tokens, BigInteger)
    assert isinstance(cache_read_tokens, BigInteger)

    for field in (
        "total_input_cost_usd",
        "total_output_cost_usd",
        "total_cache_write_cost_usd",
        "total_cache_read_cost_usd",
        "total_estimated_cost_usd",
    ):
        column_type = columns[field].type
        assert isinstance(column_type, Numeric)
        assert column_type.precision == 15
        assert column_type.scale == 6


def test_user_model_has_monthly_budget() -> None:
    columns = UserModel.__table__.columns
    assert "monthly_budget_usd" in columns

    budget_type = columns["monthly_budget_usd"].type
    assert isinstance(budget_type, Numeric)
    assert budget_type.precision == 12
    assert budget_type.scale == 2
