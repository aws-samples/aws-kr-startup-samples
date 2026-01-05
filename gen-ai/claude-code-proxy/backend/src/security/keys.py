import hmac
import hashlib
import secrets
import base64
import re

from ..config import get_settings


class KeyHasher:
    """HMAC-SHA256 based key hashing."""

    def __init__(self, secret: str | None = None):
        self._secret = (secret or get_settings().key_hasher_secret).encode()

    def hash(self, raw_key: str) -> str:
        return hmac.new(self._secret, raw_key.encode(), hashlib.sha256).hexdigest()

    def verify(self, raw_key: str, stored_hash: str) -> bool:
        computed = self.hash(raw_key)
        return hmac.compare_digest(computed, stored_hash)


class KeyGenerator:
    """Secure access key generation."""

    PREFIX = "ak_"
    KEY_BYTES = 32

    @classmethod
    def generate(cls) -> str:
        random_bytes = secrets.token_bytes(cls.KEY_BYTES)
        encoded = base64.urlsafe_b64encode(random_bytes).decode().rstrip("=")
        return f"{cls.PREFIX}{encoded}"

    @classmethod
    def get_prefix(cls, raw_key: str) -> str:
        """Extract display prefix (ak_ + 6 chars)."""
        if raw_key.startswith(cls.PREFIX):
            return raw_key[: len(cls.PREFIX) + 6]
        return raw_key[:9]


class KeyMasker:
    """Mask sensitive keys in logs."""

    PATTERNS = [
        (re.compile(r"ak_[A-Za-z0-9_-]+"), "ak_***"),
        (re.compile(r"Bearer\s+[A-Za-z0-9_-]+"), "Bearer ***"),
    ]

    @classmethod
    def mask(cls, text: str) -> str:
        for pattern, replacement in cls.PATTERNS:
            text = pattern.sub(replacement, text)
        return text
