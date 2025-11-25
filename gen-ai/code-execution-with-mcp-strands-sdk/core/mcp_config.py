"""MCP server configuration and utilities."""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from mcp import StdioServerParameters, stdio_client
from strands.tools.mcp import MCPAgentTool, MCPClient
from strands.tools.mcp.mcp_types import MCPToolResult
from strands.types.collections import PaginatedList

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: List[str]
    env: Dict[str, str]

    def parameters(self) -> StdioServerParameters:
        """Convert config to StdioServerParameters for MCP client."""
        return StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env if self.env else None,
        )


def _default_log_file(filename: str) -> str:
    """Generate default log file path in project root."""
    return str(Path(__file__).parent.parent / filename)


# Registry of available MCP servers
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


def build_mcp_clients(startup_timeout: int = 60) -> list[MCPClient]:
    """Build MCP clients for all configured servers.
    
    Args:
        startup_timeout: Timeout in seconds for client initialization (default: 60).
        
    Returns:
        List of MCPClient instances.
    """
    clients: list[MCPClient] = []
    timeout = int(os.getenv("MCP_STARTUP_TIMEOUT", startup_timeout))
    
    logger.info("Building MCP clients with startup_timeout=%d seconds", timeout)
    
    for config in MCP_REGISTRY.values():
        parameters = config.parameters()
        client = MCPClient(
            lambda params=parameters: stdio_client(params),
            startup_timeout=timeout,
        )
        clients.append(client)
        logger.debug("Created MCPClient for server: %s", config.name)
    
    logger.info("Built %d MCP clients", len(clients))
    return clients


def list_all_tools(client: MCPClient) -> list[MCPAgentTool]:
    """List all available tools from an MCP client with pagination.
    
    Args:
        client: MCP client instance.
        
    Returns:
        List of all available tools.
    """
    tools: list[MCPAgentTool] = []
    pagination_token: Optional[str] = None
    while True:
        page: PaginatedList[MCPAgentTool] = client.list_tools_sync(pagination_token)
        tools.extend(page)
        if page.pagination_token is None:
            break
        pagination_token = page.pagination_token
    return tools


@contextmanager
def mcp_session(server_key: str, startup_timeout: int = 60) -> MCPClient:
    """Create a context-managed MCP client session.
    
    Args:
        server_key: Key from MCP_REGISTRY to identify the server.
        startup_timeout: Timeout in seconds for client initialization (default: 60).
        
    Yields:
        Connected MCP client instance.
    """
    config = MCP_REGISTRY[server_key]
    timeout = int(os.getenv("MCP_STARTUP_TIMEOUT", startup_timeout))
    
    logger.info(
        "Starting MCP session for server: %s (command: %s %s, timeout=%ds)",
        server_key,
        config.command,
        " ".join(config.args[:2]) + ("..." if len(config.args) > 2 else ""),
        timeout,
    )
    client = MCPClient(
        lambda params=config.parameters(): stdio_client(params),
        startup_timeout=timeout,
    )
    try:
        with client:
            logger.debug("MCP client connected for server: %s", server_key)
            yield client
            logger.debug("MCP client session ending for server: %s", server_key)
    except Exception as e:
        logger.error(
            "Error in MCP session for server %s: %s",
            server_key,
            e,
            exc_info=True,
        )
        raise
    finally:
        logger.info("MCP session closed for server: %s", server_key)


def call_mcp_tool(
    server_key: str, tool_name: str, arguments: Optional[dict] = None
) -> MCPToolResult:
    """Invoke a single MCP tool by name and return the result.
    
    Args:
        server_key: Key from MCP_REGISTRY to identify the server.
        tool_name: Name of the tool to invoke.
        arguments: Optional arguments dictionary for the tool.
        
    Returns:
        Result from the MCP tool invocation.
    """
    tool_use_id = str(uuid.uuid4())
    args_dict = arguments or {}
    
    logger.info(
        "Calling MCP tool: server=%s, tool=%s, tool_use_id=%s, arguments=%s",
        server_key,
        tool_name,
        tool_use_id,
        args_dict,
    )
    
    try:
        with mcp_session(server_key) as client:
            logger.debug(
                "Invoking MCP tool via call_tool_sync: server=%s, tool=%s, tool_use_id=%s",
                server_key,
                tool_name,
                tool_use_id,
            )
            
            result = client.call_tool_sync(tool_use_id, tool_name, args_dict)
            
            # Log result summary (avoid logging full content if too large)
            result_str = str(result)
            if len(result_str) > 500:
                result_summary = result_str[:500] + "... (truncated)"
            else:
                result_summary = result_str
            
            logger.info(
                "MCP tool call completed: server=%s, tool=%s, tool_use_id=%s, result_length=%d",
                server_key,
                tool_name,
                tool_use_id,
                len(result_str),
            )
            logger.debug(
                "MCP tool result: server=%s, tool=%s, result=%s",
                server_key,
                tool_name,
                result_summary,
            )
            
            return result
            
    except Exception as e:
        logger.error(
            "Error calling MCP tool: server=%s, tool=%s, tool_use_id=%s, error=%s",
            server_key,
            tool_name,
            tool_use_id,
            e,
            exc_info=True,
        )
        raise

