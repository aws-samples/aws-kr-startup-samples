from __future__ import annotations

from ..base import call_mcp_tool

SERVER_KEY = "amazon-ecs"


def get_deployment_status(cluster_name: str, *, service_name: str):
    """Retrieve deployment status using the `get_deployment_status` tool."""
    payload = {"cluster_name": cluster_name, "service_name": service_name}
    return call_mcp_tool(SERVER_KEY, "get_deployment_status", payload)

