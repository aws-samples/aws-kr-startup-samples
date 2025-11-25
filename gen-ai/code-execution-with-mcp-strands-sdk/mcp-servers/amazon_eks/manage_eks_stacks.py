from __future__ import annotations

from typing import Optional

from core.mcp_config import call_mcp_tool

SERVER_KEY = "amazon-eks"


def manage_eks_stacks(
    action: str, *, stack_name: str, parameters: Optional[dict] = None
):
    """Trigger CloudFormation-based EKS workflows via `manage_eks_stacks`."""
    payload = {"action": action, "stack_name": stack_name}
    if parameters:
        payload["parameters"] = parameters
    return call_mcp_tool(SERVER_KEY, "manage_eks_stacks", payload)

