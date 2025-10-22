"""MCP client integration for tool management."""
from typing import Any, Dict, List, Optional, Callable

from mcp import stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from strands import tool, Agent
from strands.tools.mcp import MCPClient

from .settings import MCPServerConfig, Settings


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self, mcp_server_configs: List[MCPServerConfig]):
        """Initialize the tool registry.
        
        Args:
            settings: The settings to use.
        """
        self.mcp_server_configs = mcp_server_configs
        self.mcp_clients = self._create_mcp_clients()
        self.tools = []
    
    def _create_mcp_clients(self) -> List[MCPClient]:
        """Create MCP clients from settings.
        
        Returns:
            List[MCPClient]: The created MCP clients.
        """
        clients = []
        for server_config in self.mcp_server_configs:
            clients.append(self._create_mcp_client(server_config))
        return clients
    
    def _create_mcp_client(self, config: MCPServerConfig) -> MCPClient:
        """Create an MCP client from a configuration.
        
        Args:
            config: The MCP server configuration.
            
        Returns:
            MCPClient: The created MCP client.
        """
        if config.transport == "stdio":
            return MCPClient(lambda: stdio_client(
                StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=config.env
                )
            ))
        elif config.transport == "streamablehttp":
            return MCPClient(
                lambda url=config.url: streamablehttp_client(url)
            )
        else:
            raise ValueError(f"Unsupported transport type: {config.transport}")
    
    def register_tools_from_mcp(self) -> None:
        """Register tools from all MCP clients."""
        for client in self.mcp_clients:
            # Get tools from MCP client
            client.__enter__()
            tools = client.list_tools_sync()
            for t in tools:
                self.tools.append(t)

    def cleanup(self):
        """Clean up MCP clients and sessions."""
        for client in self.mcp_clients:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass
        
        self.mcp_clients.clear()
        self.tools.clear()

    def get_agent_tools(self):
        """Get all tools as AgentTools.
        
        Returns:
            List[AgentTool]: The list of tools as AgentTools.
        """
        return self.tools