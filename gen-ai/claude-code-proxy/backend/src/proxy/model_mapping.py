from dataclasses import dataclass
from typing import Mapping

from ..config import get_settings

DEFAULT_BEDROCK_MODEL = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

DEFAULT_MODEL_MAPPING: dict[str, str] = {
    "claude-haiku-4-5-20251001": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "claude-sonnet-4-5-20250929": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "claude-opus-4-5-20251101": "global.anthropic.claude-opus-4-5-20251101-v1:0",
}


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


def build_default_bedrock_model_resolver() -> BedrockModelResolver:
    settings = get_settings()
    mapping = dict(DEFAULT_MODEL_MAPPING)
    if settings.bedrock_model_mapping:
        mapping.update(settings.bedrock_model_mapping)
    return BedrockModelResolver(mapping=mapping, default_model=DEFAULT_BEDROCK_MODEL)
