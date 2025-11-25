"""MCP Direct Agent - Strands agent with direct MCP server connections.

This agent instantiates AWS documentation, EKS, ECS, and CDK MCP servers
up front and handles prompts using the listed tools (classic direct tool approach).
"""

from __future__ import annotations

import argparse
import os
from contextlib import ExitStack

from dotenv import load_dotenv
from strands import Agent
from strands.tools.mcp import MCPAgentTool

from core import (
    LANGFUSE_CLIENT,
    build_mcp_clients,
    list_all_tools,
    setup_logging,
    traced_run,
)

load_dotenv()
logger = setup_logging()


def execute_agent(prompt: str) -> str:
    """Instantiate the MCP-backed agent and run the prompt.
    
    Args:
        prompt: User query to execute.
        
    Returns:
        Agent response string.
    """
    clients = build_mcp_clients()
    tools: list[MCPAgentTool] = []
    successful_clients = []
    
    logger.info("Initializing %d MCP clients...", len(clients))
    
    with ExitStack() as stack:
        # Initialize clients one by one with error handling
        for i, client in enumerate(clients):
            try:
                logger.info("Initializing MCP client %d/%d...", i + 1, len(clients))
                stack.enter_context(client)
                successful_clients.append(client)
                logger.info("MCP client %d/%d initialized successfully", i + 1, len(clients))
            except Exception as e:
                logger.warning(
                    "Failed to initialize MCP client %d/%d: %s. Continuing with other clients.",
                    i + 1,
                    len(clients),
                    e,
                )
                # Continue with other clients even if one fails
        
        if not successful_clients:
            logger.error("No MCP clients initialized successfully. Agent will run without MCP tools.")
        else:
            logger.info("Successfully initialized %d/%d MCP clients", len(successful_clients), len(clients))
        
        # Collect tools from successfully initialized clients
        for client in successful_clients:
            try:
                client_tools = list_all_tools(client)
                tools.extend(client_tools)
                logger.debug("Collected %d tools from client", len(client_tools))
            except Exception as e:
                logger.warning("Failed to list tools from client: %s", e)
        
        logger.info("Total tools available: %d", len(tools))
        
        agent = Agent(
            model="global.anthropic.claude-haiku-4-5-20251001-v1:0",
            tools=tools
        )
        return agent(prompt)


def run(prompt: str, user_id: str | None = None) -> str:
    """Run the Strands agent and capture traces.
    
    Args:
        prompt: User query to execute.
        user_id: Optional user identifier for Langfuse traces.
        
    Returns:
        Agent response string.
    """
    logger.info("Starting prompt execution: %s", prompt)
    with traced_run(prompt, user_id) as span:
        response = execute_agent(prompt)
        if span is not None:
            # Set output on the span (Langfuse v3 uses attribute assignment)
            span.output = {"response": response}
    logger.info("Prompt execution finished.")
    return response


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Strands MCP Direct Agent with Langfuse tracing"
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="What is AWS Lambda?",
        help="Question to ask the agent",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("LANGFUSE_USER_ID", "local-user"),
        help="User ID to record in Langfuse trace",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the MCP Direct Agent."""
    args = parse_args()
    response = run(args.prompt, args.user_id)
    print(response)


if __name__ == "__main__":
    main()

