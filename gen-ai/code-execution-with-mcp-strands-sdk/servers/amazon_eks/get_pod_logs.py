from __future__ import annotations

from typing import Optional

from ..base import call_mcp_tool

SERVER_KEY = "amazon-eks"


def get_pod_logs(
    cluster_name: str,
    *,
    pod_name: str,
    namespace: str,
    container_name: Optional[str] = None,
    tail_lines: int = 200,
):
    """Fetch recent pod logs using the `get_pod_logs` MCP tool."""
    payload = {
        "cluster_name": cluster_name,
        "pod_name": pod_name,
        "namespace": namespace,
        "tail_lines": tail_lines,
    }
    if container_name:
        payload["container_name"] = container_name
    return call_mcp_tool(SERVER_KEY, "get_pod_logs", payload)

