"""Tools module for the observability agent."""

from .tool_registry import ToolRegistry

def get_tool_registry() -> ToolRegistry:
    """Get the singleton ToolRegistry instance.
    
    Returns:
        ToolRegistry: The singleton ToolRegistry instance.
        
    Raises:
        RuntimeError: If the ToolRegistry singleton has not been initialized.
    """
    instance = ToolRegistry.get_instance()
    if not ToolRegistry.is_initialized():
        raise RuntimeError("ToolRegistry singleton not initialized. Initialize it in main() first.")
    return instance

def get_tool_by_name(name: str):
    """Get a tool by its name using the singleton ToolRegistry.
    
    Args:
        name: The name of the tool to retrieve.
        
    Returns:
        Tool: The tool object if found, None otherwise.
        
    Raises:
        RuntimeError: If the ToolRegistry singleton has not been initialized.
    """
    registry = get_tool_registry()
    return registry.get_tool_by_name(name)

def get_all_tools():
    """Get all tools for use with an Agent.
    
    Returns:
        List of tools that can be used with strands Agent.
        
    Raises:
        RuntimeError: If the ToolRegistry singleton has not been initialized.
    """
    registry = get_tool_registry()
    return registry.get_all_tools()

__all__ = [
    'ToolRegistry',
    'get_tool_registry',
    'get_tool_by_name',
    'get_all_tools'
] 