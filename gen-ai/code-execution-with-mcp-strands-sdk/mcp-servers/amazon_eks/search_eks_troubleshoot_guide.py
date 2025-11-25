from __future__ import annotations

from typing import Optional

from core.mcp_config import call_mcp_tool

SERVER_KEY = "amazon-eks"


def search_eks_troubleshoot_guide(query: str, *, cluster_name: Optional[str] = None):
    """Search curated EKS troubleshooting guides for the provided query."""
    payload = {"query": query}
    if cluster_name:
        payload["cluster_name"] = cluster_name
    return call_mcp_tool(SERVER_KEY, "search_eks_troubleshoot_guide", payload)

