from __future__ import annotations

from typing import Optional

from ..base import call_mcp_tool

SERVER_KEY = "amazon-ecs"


def create_ecs_infrastructure(stack_name: str, *, parameters: Optional[dict] = None):
    """Provision ECS infrastructure via the `create_ecs_infrastructure` tool."""
    payload = {"stack_name": stack_name}
    if parameters:
        payload["parameters"] = parameters
    return call_mcp_tool(SERVER_KEY, "create_ecs_infrastructure", payload)

