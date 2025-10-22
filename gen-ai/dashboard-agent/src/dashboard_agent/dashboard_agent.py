"""Agent module for the dashboard agent."""

from typing import Any, Dict, List

import resend
from strands import Agent, tool
from strands_tools import file_read, file_write

from .settings import Settings, get_default_settings
from .tool_registry import ToolRegistry
from .feedback_learning_agent import feedback_learning_agent
from .analysis_tool import analysis_tool

DASHBOARD_AGENT_SYSTEM_PROMPT = """
You are a comprehensive dashboard agent that processes data from Google Drive spreadsheets, generates reports, and continuously improves prompts based on Slack feedback.

Your role is to:

1. Data Processing Workflow
   - Read data from Google Drive spreadsheets using Google Drive MCP tools
   - Process data through a three-stage pipeline using the latest versioned prompts:
     * Extraction: Extract relevant information from spreadsheet data
     * Analysis: Analyze the extracted data for insights and patterns
     * Report Generation: Create comprehensive reports based on the analysis
   - Always use the latest version of prompts located in the prompts/ directory (e.g., v1.2.0)

2. Feedback Collection and Prompt Enhancement
   - Monitor and collect feedback from designated Slack channels using Slack MCP tools
   - Analyze feedback to identify prompt improvement opportunities
   - When feedback indicates prompt issues or enhancement needs, use the feedback_learning_agent tool to:
     * Create new semantically versioned prompts based on the feedback
     * Preserve all previous prompt versions for rollback capability
     * Document changes in the version history

3. Key Responsibilities
   - Execute the full data processing pipeline: read → extract → analyze → report
   - Maintain high-quality outputs by using the most current prompt versions
   - Actively collect and process user feedback from Slack channels
   - Continuously improve prompts through iterative feedback-driven enhancements
   - Coordinate between Google Drive data access, report generation, and feedback processing

4. Decision Protocol
   - For data processing requests → Use Google Drive MCP tools to read spreadsheet, then use analysis_tool to process data
   - For feedback collection → Use Slack MCP tools to read from feedback channels
   - For prompt improvements → Use feedback_learning_agent tool with collected feedback
   - The analysis_tool automatically uses the latest prompt version

5. Workflow Example
   a) User requests a report from a Google Drive spreadsheet
   b) Read spreadsheet data using Google Drive MCP tools (gsheets_read)
   c) Pass the JSON output from gsheets_read to analysis_tool
   d) The analysis_tool will automatically:
      - Load latest prompt versions (extraction.txt, analysis.txt, report.txt)
      - Execute extraction → analysis → report generation pipeline
   e) Deliver the final report from analysis_tool
   f) Monitor Slack for feedback on the report quality
   g) If feedback suggests improvements, call feedback_learning_agent to create new prompt versions
"""


class DashboardAgent:
    """Dashboard agent with workflow and tool execution capabilities."""

    def __init__(self, settings: Settings = None):
        """Initialize the dashboard agent.

        Args:
            settings: The settings to use. If None, default settings will be used.
        """
        self.settings = settings or get_default_settings()
        mcp_servers = [self.settings.mcp_servers.get('slack'), self.settings.mcp_servers.get('gdrive')]
        self.tool_registry = ToolRegistry(mcp_servers)

        # Initialize the agent
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """Create the agent.

        Returns:
            Agent: The created agent.
        """
        # Register tools from MCP
        self.tool_registry.register_tools_from_mcp()

        # Get all tools as AgentTools
        tools = self.tool_registry.get_agent_tools()
        tools.append(feedback_learning_agent)
        tools.append(analysis_tool)

        # Create the agent with all tools
        agent = Agent(
            model=self.settings.bedrock.model_id,
            system_prompt=DASHBOARD_AGENT_SYSTEM_PROMPT,
            tools=tools,
            callback_handler=None,
        )

        return agent

    def process_message(self, message: str):
        """Process a user message.

        Args:
            message: The user message to process.

        Returns:
            Stream: A stream of the assistant's response.
        """
        return self.agent.stream_async(message)
