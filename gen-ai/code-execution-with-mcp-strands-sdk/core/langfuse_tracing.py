"""Langfuse tracing utilities shared across agents."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Optional

from langfuse import Langfuse, get_client

from .logging import logger


def init_langfuse_client() -> Optional[Langfuse]:
    """Initialize Langfuse client if credentials are present.
    
    Returns:
        Langfuse client instance or None if credentials are missing.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not (public_key and secret_key):
        logger.warning("Langfuse credentials not found; tracing disabled.")
        return None

    Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    client = get_client()
    logger.info("Langfuse tracing enabled for %s.", host)
    return client


# Global Langfuse client (lazy initialization on first access)
_LANGFUSE_CLIENT: Optional[Langfuse] = None


def _get_langfuse_client() -> Optional[Langfuse]:
    """Get or initialize the Langfuse client (lazy initialization).
    
    Returns:
        Langfuse client instance or None if credentials are missing.
    """
    global _LANGFUSE_CLIENT
    if _LANGFUSE_CLIENT is None:
        _LANGFUSE_CLIENT = init_langfuse_client()
    return _LANGFUSE_CLIENT


# Expose as a module-level variable that gets initialized on first access
# This allows lazy initialization after load_dotenv() is called
class _LangfuseClientProxy:
    """Proxy object that initializes Langfuse client on first access."""
    
    def __getattr__(self, name: str):
        client = _get_langfuse_client()
        if client is None:
            raise AttributeError(f"Langfuse client is not initialized. {name}")
        return getattr(client, name)
    
    def __bool__(self) -> bool:
        return _get_langfuse_client() is not None
    
    def __call__(self, *args, **kwargs):
        client = _get_langfuse_client()
        if client is None:
            return None
        return client(*args, **kwargs)


LANGFUSE_CLIENT = _LangfuseClientProxy()


@contextmanager
def traced_run(
    prompt: str, user_id: Optional[str] = None
) -> Generator[Optional[object], None, None]:
    """Wrap an agent run in a Langfuse span if configured.
    
    Args:
        prompt: The user prompt being executed.
        user_id: Optional user identifier for the trace.
        
    Yields:
        Langfuse span object or None if tracing is disabled.
    """
    client = _get_langfuse_client()
    if client is None:
        yield None
        return

    final_user_id = user_id or os.getenv("LANGFUSE_USER_ID")
    
    # Langfuse v3: Use start_as_current_span to create a trace/span
    # The span will automatically create a trace if one doesn't exist
    with client.start_as_current_span(
        name="strands-agent-run",
        input={"prompt": prompt},
    ) as span:
        # Set user_id on the current trace
        if final_user_id:
            client.update_current_trace(user_id=final_user_id)
        
        try:
            yield span
        finally:
            # Ensure data is flushed to Langfuse
            client.flush()

