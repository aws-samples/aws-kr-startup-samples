from __future__ import annotations

from typing import Optional

from ..base import call_mcp_tool

SERVER_KEY = "amazon-ecs"


def containerize_app(
    source_path: str,
    *,
    runtime: Optional[str] = None,
    optimization_level: Optional[str] = None,
):
    """Use the `containerize_app` tool to build container artifacts with best practices."""
    payload = {"source_path": source_path}
    if runtime:
        payload["runtime"] = runtime
    if optimization_level:
        payload["optimization_level"] = optimization_level
    return call_mcp_tool(SERVER_KEY, "containerize_app", payload)

