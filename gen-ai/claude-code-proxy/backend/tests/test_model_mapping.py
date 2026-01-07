from src.config import get_settings
from src.proxy.model_mapping import (
    DEFAULT_BEDROCK_MODEL,
    build_default_bedrock_model_resolver,
)


def test_resolver_resolves_db_mappings() -> None:
    """Test that resolver correctly resolves mappings passed from DB."""
    db_mappings = {
        "claude-haiku-4-5-20251001": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "claude-sonnet-4-5-20250929": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    }
    resolver = build_default_bedrock_model_resolver(db_mappings=db_mappings)
    for requested, expected in db_mappings.items():
        assert resolver.resolve(requested) == expected


def test_resolver_falls_back_to_default_model() -> None:
    """Test that unknown models fall back to DEFAULT_BEDROCK_MODEL."""
    resolver = build_default_bedrock_model_resolver()
    assert resolver.resolve("claude-unknown") == DEFAULT_BEDROCK_MODEL


def test_resolver_preserves_bedrock_model_ids() -> None:
    """Test that Bedrock model IDs pass through unchanged."""
    resolver = build_default_bedrock_model_resolver()
    bedrock_id = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    assert resolver.resolve(bedrock_id) == bedrock_id


def test_env_mapping_overrides_db_mappings(monkeypatch) -> None:
    """Test that env var mappings override DB mappings."""
    db_mappings = {"claude-test": "global.anthropic.claude-test-db-v1:0"}
    monkeypatch.setenv(
        "PROXY_BEDROCK_MODEL_MAPPING",
        '{"claude-test":"global.anthropic.claude-test-env-v1:0"}',
    )
    get_settings.cache_clear()
    resolver = build_default_bedrock_model_resolver(db_mappings=db_mappings)
    # Env var should override DB mapping
    assert resolver.resolve("claude-test") == "global.anthropic.claude-test-env-v1:0"
    get_settings.cache_clear()
