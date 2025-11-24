from __future__ import annotations

from typing import Optional

from ..base import call_mcp_tool

SERVER_KEY = "aws-documentation"


def search_documentation(
    search_phrase: str, *, limit: int = 5, filters: Optional[dict] = None
):
    """Query AWS documentation for recent guidance (see `search_documentation` tool docs)."""
    payload: dict = {"search_phrase": search_phrase, "limit": limit}
    if filters:
        payload["filters"] = filters
    return call_mcp_tool(SERVER_KEY, "search_documentation", payload)

