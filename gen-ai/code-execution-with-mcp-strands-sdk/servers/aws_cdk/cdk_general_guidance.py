from __future__ import annotations

from typing import Optional

from ..base import call_mcp_tool

SERVER_KEY = "aws-cdk"


def cdk_general_guidance(context: Optional[str] = None):
    """Retrieve best practices via the `CDKGeneralGuidance` tool."""
    payload = {"context": context} if context else {}
    return call_mcp_tool(SERVER_KEY, "CDKGeneralGuidance", payload)

