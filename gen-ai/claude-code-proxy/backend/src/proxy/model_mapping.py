from dataclasses import dataclass
from typing import Literal, Mapping

from ..config import get_settings

ModelSlotName = Literal["opus", "sonnet", "haiku"]
DEFAULT_BEDROCK_MODEL = "global.anthropic.claude-sonnet-4-6"
DEFAULT_SLOT_MODELS: dict[ModelSlotName, str] = {
    "opus": "global.anthropic.claude-opus-4-6-v1",
    "sonnet": DEFAULT_BEDROCK_MODEL,
    "haiku": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
}

_model_slot_cache: dict[str, str] | None = None


def invalidate_model_slot_cache() -> None:
    global _model_slot_cache
    _model_slot_cache = None


def get_cached_model_slots() -> dict[str, str] | None:
    return _model_slot_cache


def set_cached_model_slots(slots: dict[str, str]) -> None:
    global _model_slot_cache
    _model_slot_cache = slots


def get_default_model_targets() -> dict[str, str]:
    settings = get_settings()
    return {
        "anthropic_default_opus_model": settings.anthropic_default_opus_model,
        "anthropic_default_sonnet_model": settings.anthropic_default_sonnet_model,
        "anthropic_default_haiku_model": settings.anthropic_default_haiku_model,
    }


def get_default_slot_models() -> dict[str, str]:
    settings = get_settings()
    return {
        "opus": settings.anthropic_default_opus_model,
        "sonnet": settings.anthropic_default_sonnet_model,
        "haiku": settings.anthropic_default_haiku_model,
    }


def detect_model_slot(requested_model: str | None) -> ModelSlotName:
    if not requested_model:
        return "sonnet"
    model = requested_model.lower()
    if "opus" in model:
        return "opus"
    if "haiku" in model:
        return "haiku"
    return "sonnet"


def get_effective_slot_model(slot: ModelSlotName) -> str:
    cached = get_cached_model_slots() or {}
    if slot in cached:
        return cached[slot]
    return get_default_slot_models().get(slot, DEFAULT_SLOT_MODELS[slot])


@dataclass(frozen=True)
class BedrockModelResolver:
    slots: Mapping[str, str]
    default_model: str = DEFAULT_BEDROCK_MODEL

    def resolve(self, requested_model: str | None) -> str:
        slot = detect_model_slot(requested_model)
        if slot in self.slots:
            return self.slots[slot]
        return self.slots.get("sonnet", self.default_model)


def build_default_bedrock_model_resolver(
    model_slots: dict[str, str] | None = None,
) -> BedrockModelResolver:
    settings = get_settings()

    slots = get_default_slot_models()
    slots.update(get_cached_model_slots() or {})
    if model_slots:
        slots.update(model_slots)

    return BedrockModelResolver(
        slots=slots,
        default_model=slots.get("sonnet", settings.bedrock_default_model or DEFAULT_BEDROCK_MODEL),
    )
