"""Coordinator agent that manages the main observability agent and its resources."""
import os
from typing import Optional, List, Any, Dict
from strands import Agent
from strands.models import BedrockModel

from observability_agent.agents.trace_to_logs import trace_to_logs
from observability_agent.datasources.cache import load_datasources_config
from observability_agent.config.settings import get_default_settings, Settings
from observability_agent.mcp import ToolRegistry


SYSTEM_PROMPT = """
You are a specialized observability agent that helps users analyze traces, logs, and metrics.
You can help users find logs related to trace IDs, query observability data, and provide insights.

When a user asks for logs related to a trace ID, use the trace_to_logs tool which will:
1. Fetch the tracesToLogs configuration from Grafana Tempo datasource  
2. Formulate appropriate LogQL queries
3. Execute the queries and return formatted results

Be helpful and provide clear, actionable information about observability data.
"""


class CoordinatorAgent:
    """
    Coordinator agent that manages the main observability agent and its resources.
    
    This class encapsulates the initialization, configuration, and cleanup logic
    for the observability agent, providing a consistent interface for both
    CLI and web interfaces.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the coordinator agent.
        
        Args:
            settings: Optional settings object. If not provided, will load defaults.
        """
        self.settings = settings or get_default_settings()
        self.tool_registry: Optional[ToolRegistry] = None
        self.agent: Optional[Agent] = None
        self.datasources_config: Dict[str, Any] = {}
        self._initialized = False
    
    def initialize(self) -> 'CoordinatorAgent':
        """
        Initialize all components of the coordinator agent.
        
        Returns:
            Self for method chaining.
            
        Raises:
            Exception: If initialization fails.
        """
        if self._initialized:
            return self
        
        try:
            # Initialize the singleton ToolRegistry
            self.tool_registry = ToolRegistry.get_instance(self.settings)
            self.tool_registry.initialize()
            
            # Load datasources configuration (continue even if it fails)
            try:
                self.datasources_config = load_datasources_config()
                print(f"✅ Datasources configuration loaded: {list(self.datasources_config.keys())}")
            except Exception as e:
                # Continue without datasources config if it fails
                self.datasources_config = {}
                print(f"⚠️  Could not load datasources configuration: {e}")
                print("   The agent will work with limited functionality...")
            
            # Collect available tools (after tool registry is initialized)
            available_tools = self._collect_available_tools()

            # Create the main agent
            self.agent = Agent(
                system_prompt=SYSTEM_PROMPT,
                model=self.settings.bedrock_model,
                tools=available_tools,
                callback_handler=None
            )
            
            self._initialized = True
            print(f"🎉 CoordinatorAgent initialized successfully with {len(available_tools)} tools!")
            return self
            
        except Exception as e:
            # Clean up on failure
            self.cleanup()
            raise e
    
    def _collect_available_tools(self) -> List[Any]:
        """
        Collect all available tools for the agent.
        
        Returns:
            List of available tools.
        """
        available_tools = []
        
        # Get MCP tools (only if tool registry is initialized)
        if self.tool_registry and self.tool_registry.is_initialized():
            try:
                mcp_tools = self.tool_registry.get_all_tools()
                available_tools.extend(mcp_tools)
            except Exception:
                # Continue without MCP tools if they fail to load
                pass
        
        # Add the trace_to_logs function
        available_tools.append(trace_to_logs)
        
        return available_tools
    
    def get_agent(self) -> Agent:
        """
        Get the underlying agent instance.
        
        Returns:
            The initialized agent.
            
        Raises:
            RuntimeError: If the coordinator is not initialized.
        """
        if not self._initialized or self.agent is None:
            raise RuntimeError("CoordinatorAgent not initialized. Call initialize() first.")
        return self.agent
    
    def is_initialized(self) -> bool:
        """
        Check if the coordinator agent is initialized.
        
        Returns:
            True if initialized, False otherwise.
        """
        return self._initialized
    
    def get_datasources_config(self) -> Dict[str, Any]:
        """
        Get the loaded datasources configuration.
        
        Returns:
            Dictionary containing datasources configuration.
        """
        return self.datasources_config
    
    def get_datasource_greeting(self) -> str:
        """
        Generate a greeting message with available datasources.
        
        Returns:
            Formatted greeting string with datasource information.
        """
        if not self.datasources_config:
            return "⚠️  No datasources currently available. Some features may be limited."
        
        greeting_parts = ["🔍 **Observability Assistant Ready!**  \n  \n"]
        greeting_parts.append("📊 **Available Datasources:**  \n")
        
        for ds_type, config in self.datasources_config.items():
            details = config.get('details', {})
            ds_name = details.get('name', f'Unnamed {ds_type}')
            ds_type_display = details.get('type', ds_type).title()
            ds_url = details.get('url', 'Unknown URL')
            greeting_parts.append(f"• **{ds_type_display}**: {ds_name} ({ds_url})  \n")
        
        greeting_parts.append("\n💡 Ask me about traces, logs, metrics, or say 'help' for examples!")
        return "".join(greeting_parts)
    
    def cleanup(self) -> None:
        """
        Clean up all resources used by the coordinator agent.
        """
        if self.tool_registry:
            try:
                self.tool_registry.cleanup()
            except Exception:
                # Ignore cleanup errors
                pass
            finally:
                self.tool_registry = None
        
        self.agent = None
        self.datasources_config = {}
        self._initialized = False
    
    def __enter__(self) -> 'CoordinatorAgent':
        """Context manager entry."""
        return self.initialize()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup() 