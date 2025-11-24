from __future__ import annotations

from ..base import call_mcp_tool

SERVER_KEY = "amazon-ecs"


def delete_ecs_infrastructure(stack_name: str):
    """Tear down ECS CloudFormation stacks with `delete_ecs_infrastructure`."""
    payload = {"stack_name": stack_name}
    return call_mcp_tool(SERVER_KEY, "delete_ecs_infrastructure", payload)

