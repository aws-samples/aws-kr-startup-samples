from dataclasses import dataclass
from typing import Mapping

from ..config import get_settings

DEFAULT_BEDROCK_MODEL = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Cache for DB model mappings
_db_model_mapping_cache: dict[str, str] | None = None


def invalidate_model_mapping_cache() -> None:
    """Invalidate the cached DB model mappings."""
    global _db_model_mapping_cache
    _db_model_mapping_cache = None


def get_cached_db_mappings() -> dict[str, str] | None:
    """Get the cached DB model mappings."""
    return _db_model_mapping_cache


def set_cached_db_mappings(mappings: dict[str, str]) -> None:
    """Set the cached DB model mappings."""
    global _db_model_mapping_cache
    _db_model_mapping_cache = mappings


@dataclass(frozen=True)
class BedrockModelResolver:
    mapping: Mapping[str, str]
    default_model: str = DEFAULT_BEDROCK_MODEL

    def resolve(self, requested_model: str | None) -> str:
        if not requested_model:
            return self.default_model
        if requested_model in self.mapping:
            return self.mapping[requested_model]
        if requested_model.startswith(("global.anthropic.", "anthropic.")):
            return requested_model
        return self.default_model


def build_default_bedrock_model_resolver(
    db_mappings: dict[str, str] | None = None,
) -> BedrockModelResolver:
    """
    Build a BedrockModelResolver with mappings from multiple sources.

    Priority (later overrides earlier):
    1. DB mappings (from Admin UI, seeded via migration)
    2. Environment variable (PROXY_BEDROCK_MODEL_MAPPING) - for overrides
    """
    settings = get_settings()
    mapping: dict[str, str] = {}

    # Start with DB mappings (seeded defaults + admin-added mappings)
    if db_mappings:
        mapping.update(db_mappings)

    # Override with env var settings (useful for quick overrides without DB changes)
    if settings.bedrock_model_mapping:
        mapping.update(settings.bedrock_model_mapping)

    return BedrockModelResolver(mapping=mapping, default_model=DEFAULT_BEDROCK_MODEL)
