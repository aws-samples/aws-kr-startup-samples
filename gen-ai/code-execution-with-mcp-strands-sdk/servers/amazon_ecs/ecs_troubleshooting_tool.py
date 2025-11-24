from __future__ import annotations

from ..base import call_mcp_tool

SERVER_KEY = "amazon-ecs"


def ecs_troubleshooting_tool(action: str, **parameters):
    """Call the unified `ecs_troubleshooting_tool` for diagnostics."""
    payload = {"action": action, "parameters": parameters}
    return call_mcp_tool(SERVER_KEY, "ecs_troubleshooting_tool", payload)

