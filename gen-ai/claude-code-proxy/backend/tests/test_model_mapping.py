from src.config import get_settings
from src.proxy.model_mapping import (
    DEFAULT_BEDROCK_MODEL,
    DEFAULT_MODEL_MAPPING,
    build_default_bedrock_model_resolver,
)


def test_default_model_mapping_resolves_known_models() -> None:
    resolver = build_default_bedrock_model_resolver()
    for requested, expected in DEFAULT_MODEL_MAPPING.items():
        assert resolver.resolve(requested) == expected


def test_default_model_mapping_falls_back_to_default() -> None:
    resolver = build_default_bedrock_model_resolver()
    assert resolver.resolve("claude-unknown") == DEFAULT_BEDROCK_MODEL


def test_default_model_mapping_preserves_bedrock_model_ids() -> None:
    resolver = build_default_bedrock_model_resolver()
    bedrock_id = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    assert resolver.resolve(bedrock_id) == bedrock_id


def test_env_mapping_overrides_defaults(monkeypatch) -> None:
    monkeypatch.setenv(
        "PROXY_BEDROCK_MODEL_MAPPING",
        '{"claude-test":"global.anthropic.claude-test-v1:0"}',
    )
    get_settings.cache_clear()
    resolver = build_default_bedrock_model_resolver()
    assert resolver.resolve("claude-test") == "global.anthropic.claude-test-v1:0"
    get_settings.cache_clear()
