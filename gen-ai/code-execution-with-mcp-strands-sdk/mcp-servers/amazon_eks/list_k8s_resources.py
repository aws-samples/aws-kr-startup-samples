from __future__ import annotations

from typing import Optional

from core.mcp_config import call_mcp_tool

SERVER_KEY = "amazon-eks"


def list_k8s_resources(
    cluster_name: str,
    *,
    resource_type: str,
    namespace: Optional[str] = None,
    label_selector: Optional[str] = None,
):
    """List Kubernetes resources via the `list_k8s_resources` MCP tool."""
    payload = {
        "cluster_name": cluster_name,
        "resource_type": resource_type,
    }
    if namespace:
        payload["namespace"] = namespace
    if label_selector:
        payload["label_selector"] = label_selector
    return call_mcp_tool(SERVER_KEY, "list_k8s_resources", payload)

