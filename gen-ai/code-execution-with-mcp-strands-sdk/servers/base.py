from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from mcp import StdioServerParameters, stdio_client
from strands.tools.mcp import MCPClient, MCPToolResult

# Shared registry mirrors the MCP servers already configured in agent.py.


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    command: str
    args: Iterable[str]
    env: Dict[str, str]

    def parameters(self) -> StdioServerParameters:
        return StdioServerParameters(
            command=self.command,
            args=list(self.args),
            env=self.env if self.env else None,
        )


def _default_log_file(filename: str) -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", filename)
    )


MCP_REGISTRY: Dict[str, MCPServerConfig] = {
    "aws-documentation": MCPServerConfig(
        name="aws-documentation",
        command="uvx",
        args=["awslabs.aws-documentation-mcp-server@latest"],
        env={"FASTMCP_LOG_LEVEL": os.getenv("AWS_DOCS_MCP_LOG_LEVEL", "ERROR")},
    ),
    "amazon-eks": MCPServerConfig(
        name="amazon-eks",
        command="uvx",
        args=[
            "awslabs.eks-mcp-server@latest",
            "--allow-write",
            "--allow-sensitive-data-access",
        ],
        env={"FASTMCP_LOG_LEVEL": os.getenv("EKS_MCP_LOG_LEVEL", "ERROR")},
    ),
    "amazon-ecs": MCPServerConfig(
        name="amazon-ecs",
        command="uvx",
        args=["--from", "awslabs-ecs-mcp-server", "ecs-mcp-server"],
        env={
            "FASTMCP_LOG_LEVEL": os.getenv("ECS_MCP_LOG_LEVEL", "ERROR"),
            "FASTMCP_LOG_FILE": os.getenv(
                "ECS_MCP_LOG_FILE", _default_log_file("ecs-mcp-server.log")
            ),
            "ALLOW_WRITE": os.getenv("ECS_MCP_ALLOW_WRITE", "false"),
            "ALLOW_SENSITIVE_DATA": os.getenv(
                "ECS_MCP_ALLOW_SENSITIVE_DATA", "false"
            ),
        },
    ),
    "aws-cdk": MCPServerConfig(
        name="aws-cdk",
        command="uvx",
        args=["awslabs.cdk-mcp-server@latest"],
        env={"FASTMCP_LOG_LEVEL": os.getenv("CDK_MCP_LOG_LEVEL", "ERROR")},
    ),
}


@contextmanager
def mcp_session(server_key: str) -> MCPClient:
    config = MCP_REGISTRY[server_key]
    client = MCPClient(lambda params=config.parameters(): stdio_client(params))
    with client:
        yield client


def call_mcp_tool(
    server_key: str, tool_name: str, arguments: Optional[dict] = None
) -> MCPToolResult:
    """Invoke a single MCP tool by name and return the raw result."""
    with mcp_session(server_key) as client:
        tool_use_id = str(uuid.uuid4())
        return client.call_tool_sync(tool_use_id, tool_name, arguments or {})

