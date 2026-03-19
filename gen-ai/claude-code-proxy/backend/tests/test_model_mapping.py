from src.config import get_settings
from src.proxy.model_mapping import (
    DEFAULT_BEDROCK_MODEL,
    build_default_bedrock_model_resolver,
    detect_model_slot,
    get_default_model_targets,
)


def test_detect_model_slot_by_family() -> None:
    assert detect_model_slot("claude-opus-4-6-v1") == "opus"
    assert detect_model_slot("claude-haiku-4-5-20251001") == "haiku"
    assert detect_model_slot("claude-sonnet-4-6") == "sonnet"
    assert detect_model_slot("unknown-model") == "sonnet"
    assert detect_model_slot(None) == "sonnet"


def test_resolver_uses_slot_models_for_standard_requests() -> None:
    resolver = build_default_bedrock_model_resolver(
        model_slots={
            "opus": "bedrock-opus",
            "sonnet": "bedrock-sonnet",
            "haiku": "bedrock-haiku",
        }
    )

    assert resolver.resolve("claude-opus-4-6-v1") == "bedrock-opus"
    assert resolver.resolve("claude-haiku-4-5-20251001") == "bedrock-haiku"
    assert resolver.resolve("claude-sonnet-4-6") == "bedrock-sonnet"
    assert resolver.resolve("global.anthropic.claude-sonnet-4-6") == "bedrock-sonnet"
    assert resolver.resolve("claude-unknown") == "bedrock-sonnet"


def test_resolver_falls_back_to_default_model_when_no_slot_or_mapping() -> None:
    resolver = build_default_bedrock_model_resolver(model_slots={})

    assert resolver.resolve("claude-unknown") == DEFAULT_BEDROCK_MODEL


def test_default_model_targets_return_expected_builtins() -> None:
    defaults = get_default_model_targets()

    assert defaults["anthropic_default_opus_model"] == "global.anthropic.claude-opus-4-6-v1"
    assert defaults["anthropic_default_sonnet_model"] == "global.anthropic.claude-sonnet-4-6"
    assert (
        defaults["anthropic_default_haiku_model"]
        == "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    )


def test_default_model_targets_respect_env(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_DEFAULT_OPUS_MODEL", "env.opus")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "env.sonnet")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "env.haiku")
    get_settings.cache_clear()

    defaults = get_default_model_targets()

    assert defaults["anthropic_default_opus_model"] == "env.opus"
    assert defaults["anthropic_default_sonnet_model"] == "env.sonnet"
    assert defaults["anthropic_default_haiku_model"] == "env.haiku"
    get_settings.cache_clear()
