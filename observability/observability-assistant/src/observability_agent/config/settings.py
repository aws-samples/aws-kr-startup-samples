"""Settings for the observability agent."""
import os
import sys
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass


class MCPConfig(BaseModel):
    """Configuration for an MCP server."""

    grafana_mcp_url: str = Field(description="The URL of the Grafana MCP server")
    tempo_mcp_url: str = Field(description="The URL of the Tempo MCP server")


class BedrockSettings(BaseModel):
    """Settings for Amazon Bedrock."""
    
    model_id: str = Field(description="The ID of the model to use")
    region: str = Field(description="The AWS region to use")


class Settings(BaseModel):
    """Settings for the observability agent."""
    
    bedrock: BedrockSettings = Field(description="Bedrock settings")
    mcp_servers: List[MCPConfig] = Field(description="MCP server configurations")


def get_default_settings() -> Settings:
    """Get the default settings from environment variables.
    
    Returns:
        Settings: The settings loaded from environment variables.
        
    Raises:
        SystemExit: If required environment variables are not set.
    """
    # Check for required environment variables
    missing_vars = []
    
    grafana_mcp_url = os.getenv("GRAFANA_MCP_URL")
    if not grafana_mcp_url:
        missing_vars.append("GRAFANA_MCP_URL")
    
    tempo_mcp_url = os.getenv("TEMPO_MCP_URL")
    if not tempo_mcp_url:
        missing_vars.append("TEMPO_MCP_URL")
    
    if missing_vars:
        print("💥 FATAL ERROR: Required environment variables are not set!")
        print(f"Missing variables: {', '.join(missing_vars)}")
        print("\nPlease set the following environment variables:")
        for var in missing_vars:
            if var == "GRAFANA_MCP_URL":
                print(f"  export {var}=http://your-grafana-mcp-server:8000/mcp")
            elif var == "TEMPO_MCP_URL":
                print(f"  export {var}=http://your-tempo-mcp-server:8000/mcp")
        print("\nOr add them to your .env file:")
        for var in missing_vars:
            if var == "GRAFANA_MCP_URL":
                print(f"  {var}=http://your-grafana-mcp-server:8000/mcp")
            elif var == "TEMPO_MCP_URL":
                print(f"  {var}=http://your-tempo-mcp-server:8000/mcp")
        sys.exit(1)
    
    # Load Bedrock settings from environment
    bedrock_settings = BedrockSettings(
        model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-7-sonnet-20250219-v1:0"),
        region=os.getenv("BEDROCK_REGION", os.getenv("AWS_REGION", "us-east-1"))
    )
    
    # Load MCP server configuration from environment
    mcp_servers = [MCPConfig(grafana_mcp_url=grafana_mcp_url, tempo_mcp_url=tempo_mcp_url)]
    
    return Settings(
        bedrock=bedrock_settings,
        mcp_servers=mcp_servers
    ) 