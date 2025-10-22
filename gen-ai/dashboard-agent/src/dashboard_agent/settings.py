"""Settings for the dashboard agent."""

from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""

    transport: Literal["stdio", "http"] = Field(
        default="stdio", description="The transport type for the MCP server"
    )
    command: Optional[str] = Field(
        default=None, description="The command to run the MCP server (for stdio transport)"
    )
    args: Optional[List[str]] = Field(
        default=None, description="The arguments to pass to the command (for stdio transport)"
    )
    env: Optional[Dict[str, str]] = Field(
        default=None, description="Environment variables for the command (for stdio transport)"
    )
    url: Optional[str] = Field(
        default=None, description="The URL of the MCP server (for http transport)"
    )


class BedrockSettings(BaseModel):
    """Settings for Amazon Bedrock."""

    model_id: str = Field(
        # default="us.anthropic.claude-sonnet-4-20250514-v1:0",
        default="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        description="The ID of the model to use"
    )
    region: str = Field(default="us-east-1", description="The AWS region to use")
    # knowledgebase_id: str = Field(default="T7DBBSBTK9", description="The ID of the knowledge base to use")
    knowledgebase_id: str = Field(default="QPILTA6WTQ", description="The ID of the knowledge base to use")


class ResendSettings(BaseModel):
    """Settings for Resend email service."""

    api_key: Optional[str] = Field(
        default=None, description="The API key for Resend email service"
    )
    from_email: Optional[str] = Field(
        default=None, description="The default from email address"
    )


class Settings(BaseModel):
    """Settings for the dashboard agent."""

    bedrock: BedrockSettings = Field(
        default_factory=BedrockSettings, description="Bedrock settings"
    )
    resend: ResendSettings = Field(
        default_factory=ResendSettings, description="Resend email settings"
    )
    mcp_servers: Dict[str, MCPServerConfig] = Field(
        default_factory=lambda: {
            # Stdio transport: Slack MCP server
            "slack": MCPServerConfig(
                transport="stdio",
                command="npx",
                args=["-y", "slack-mcp-server@latest", "--transport", "stdio"],
                env={
                    "SLACK_MCP_XOXP_TOKEN": "xoxp",
                },
            ),
            # Stdio transport: Google Drive MCP server
            "gdrive": MCPServerConfig(
                transport="stdio",
                command="npx",
                args=[
                    "-y",
                    "@isaacphi/mcp-gdrive",
                ],
                env={
                    "CLIENT_ID": "<CLIENT_ID>",
                    "CLIENT_SECRET": "<CLIENT_SECRET>",
                    "GDRIVE_CREDS_DIR": "/path/to/config/directory"
                },
            ),
            # Example HTTP transport MCP server (uncomment and configure as needed)
            # "custom": MCPServerConfig(
            #     transport="streamablehttp",
            #     url="http://your-mcp-server:8000/mcp"
            # )
        },
        description="MCP server configurations",
    )


def get_default_settings() -> Settings:
    """Get the default settings.

    Returns:
        Settings: The default settings.
    """
    return Settings()
