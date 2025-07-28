"""MCP client integration for tool management."""
from typing import Any, Dict, List, Optional

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

from ..config.settings import Settings


class ToolRegistry:
    """Registry for managing available tools as a singleton."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, settings: Settings = None):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, settings: Settings = None):
        """Initialize the tool registry (only once).
        
        Args:
            settings: The settings to use.
        """
        # Only initialize once
        if not self._initialized:
            self.settings = settings
            self.mcp_clients = []  # List of MCPClient instances
            self.tools = []
            self.tools_by_name = {}  # Dictionary to store tools by name
            self.__class__._initialized = True
    
    @classmethod
    def get_instance(cls, settings: Settings = None) -> 'ToolRegistry':
        """Get the singleton instance.
        
        Args:
            settings: The settings to use (only used on first call).
            
        Returns:
            ToolRegistry: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = cls(settings)
        return cls._instance
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the singleton has been initialized.
        
        Returns:
            bool: True if initialized with at least one working MCP connection, False otherwise.
        """
        return (cls._instance is not None and 
                len(cls._instance.mcp_clients) > 0)
    
    def initialize(self):
        """Initialize MCP clients using Strands MCPClient with persistent connections."""
        if len(self.mcp_clients) > 0:
            # Already initialized
            return self
        
        try:
            # Create and maintain MCP connections
            self._create_persistent_connections()
            return self
        except Exception:
            # If anything fails, cleanup
            self.cleanup()
            raise
    
    def cleanup(self):
        """Clean up MCP clients and sessions."""
        for client in self.mcp_clients:
            try:
                client.__exit__(None, None, None)
            except Exception:
                pass
        
        self.mcp_clients.clear()
        self.tools.clear()
        self.tools_by_name.clear()
    
    def _create_persistent_connections(self) -> None:
        """Create persistent MCP connections that remain open using Strands MCPClient."""
        connected_count = 0
        connection_errors = []
        total_servers = 0
        
        for server_config in self.settings.mcp_servers:
            # Try to connect to Grafana MCP server
            total_servers += 1
            try:
                grafana_client = MCPClient(
                    lambda url=server_config.grafana_mcp_url: streamablehttp_client(url)
                )
                # Enter context to establish persistent connection
                grafana_client.__enter__()
                self.mcp_clients.append(grafana_client)
                self._register_tools_from_client(grafana_client, server_type="grafana")
                connected_count += 1
                print(f"✅ Successfully connected to Grafana MCP: {server_config.grafana_mcp_url}")
            except Exception as e:
                error_msg = f"Failed to connect to Grafana MCP server ({server_config.grafana_mcp_url}): {e}"
                connection_errors.append(error_msg)
                print(f"❌ {error_msg}")
            
            # Try to connect to Tempo MCP server  
            total_servers += 1
            try:
                tempo_client = MCPClient(
                    lambda url=server_config.tempo_mcp_url: streamablehttp_client(url)
                )
                # Enter context to establish persistent connection
                tempo_client.__enter__()
                self.mcp_clients.append(tempo_client)
                self._register_tools_from_client(tempo_client, server_type="tempo")
                connected_count += 1
                print(f"✅ Successfully connected to Tempo MCP: {server_config.tempo_mcp_url}")
            except Exception as e:
                error_msg = f"Failed to connect to Tempo MCP server ({server_config.tempo_mcp_url}): {e}"
                connection_errors.append(error_msg)
                print(f"❌ {error_msg}")
        
        # Fatal error if ANY MCP server failed to connect
        if connection_errors:
            print(f"\n💥 FATAL ERROR: Failed to connect to {len(connection_errors)} out of {total_servers} MCP servers!")
            print("The observability assistant requires ALL configured MCP servers to be available.")
            print("\nConnection errors:")
            for error in connection_errors:
                print(f"  • {error}")
            print("\nPlease check:")
            print("  1. MCP server URLs in your .env file are correct")
            print("  2. MCP servers are running and accessible")
            print("  3. Network connectivity to the MCP servers")
            raise RuntimeError(f"MCP server connection failures - {len(connection_errors)} of {total_servers} servers failed")
        
        print(f"🔧 ToolRegistry initialized with {connected_count} persistent MCP connections and {len(self.tools)} tools")

    def _register_tools_from_client(self, client: MCPClient, server_type: str = "unknown") -> None:
        """Register tools from a single MCP client.
        
        Args:
            client: The Strands MCPClient to get tools from.
            server_type: The type of server ("grafana", "tempo", or "unknown").
        """
        # Get tools from MCP client synchronously using Strands' sync method
        tools = client.list_tools_sync()

        # Filter tools based on server type
        filtered_tools = []
        for tool in tools:
            if server_type == "grafana":
                # For Grafana MCP server, only include tools with specific keywords in the name
                tool_name_lower = tool.tool_name.lower()
                if any(keyword in tool_name_lower for keyword in ["datasource", "prometheus", "loki"]):
                    filtered_tools.append(tool)
            else:
                # For other servers (like Tempo), add all tools
                filtered_tools.append(tool)

        # Add filtered tools to our registry
        for tool in filtered_tools:
            self.tools.append(tool)
            self.tools_by_name[tool.tool_name] = tool

    def get_all_tools(self):
        """Get all tools.
        
        Returns:
            List[Tool]: The list of tools.
        """
        if not self.is_initialized():
            raise RuntimeError("ToolRegistry not initialized. Call initialize() first.")
        return self.tools
    
    def get_tool_by_name(self, name: str):
        """Get a tool by its name.
        
        Args:
            name: The name of the tool to retrieve.
            
        Returns:
            Tool: The tool if found, None otherwise.
        """
        if not self.is_initialized():
            raise RuntimeError("ToolRegistry not initialized. Call initialize() first.")
        return self.tools_by_name.get(name) 