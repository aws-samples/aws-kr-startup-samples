from time import time
from typing import Any


class TTLCache:
    """Simple in-memory TTL cache."""

    def __init__(self, ttl: int):
        self._ttl = ttl
        self._cache: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time() > expires_at:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = (value, time() + self._ttl)

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()
