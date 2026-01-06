"""Dependency container for proxy components."""
from dataclasses import dataclass, field

from ..config import get_settings
from .cache import TTLCache
from .circuit_breaker import CircuitBreaker
from .model_mapping import BedrockModelResolver, build_default_bedrock_model_resolver


@dataclass
class ProxyDependencies:
    """Container for proxy-wide dependencies. Enables test isolation."""

    circuit_breaker: CircuitBreaker = field(default_factory=CircuitBreaker)
    access_key_cache: TTLCache = field(
        default_factory=lambda: TTLCache(get_settings().access_key_cache_ttl)
    )
    bedrock_key_cache: TTLCache = field(
        default_factory=lambda: TTLCache(get_settings().bedrock_key_cache_ttl)
    )
    bedrock_model_resolver: BedrockModelResolver = field(
        default_factory=build_default_bedrock_model_resolver
    )
    budget_cache: TTLCache = field(
        default_factory=lambda: TTLCache(get_settings().budget_cache_ttl)
    )

    def reset(self) -> None:
        """Reset all state. Useful for testing."""
        self.circuit_breaker = CircuitBreaker()
        self.access_key_cache.clear()
        self.bedrock_key_cache.clear()
        self.bedrock_model_resolver = build_default_bedrock_model_resolver()
        self.budget_cache.clear()


# Global instance (per-process)
_deps: ProxyDependencies | None = None


def get_proxy_deps() -> ProxyDependencies:
    """Get or create the global ProxyDependencies instance."""
    global _deps
    if _deps is None:
        _deps = ProxyDependencies()
    return _deps


def set_proxy_deps(deps: ProxyDependencies) -> None:
    """Override global dependencies (for testing)."""
    global _deps
    _deps = deps


def reset_proxy_deps() -> None:
    """Reset to fresh dependencies (for testing)."""
    global _deps
    _deps = ProxyDependencies()
