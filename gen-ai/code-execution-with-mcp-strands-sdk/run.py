#!/usr/bin/env python3
"""Unified run script - simplifies execution of various Strands Agents.

Usage examples:
    python run.py direct "What is AWS Lambda?"
    python run.py direct "Check EKS cluster status" --user-id demo-user
    python run.py code-exec "Create an ECS cluster"
    python run.py code-exec "List all running pods" --user-id demo-user
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables BEFORE importing modules that depend on them
load_dotenv()

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.agent_mcp_direct import run as run_direct
from agents.agent_code_execution import run as run_code_exec
from core.logging import setup_logging

logger = setup_logging()


AGENT_TYPES = {
    "direct": {
        "name": "MCP Direct Agent",
        "description": "Agent with direct MCP server connections",
        "runner": run_direct,
    },
    "code-exec": {
        "name": "Code Execution Agent",
        "description": "Agent with dynamic tool discovery and code execution",
        "runner": run_code_exec,
    },
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Strands Agent unified runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "agent_type",
        choices=list(AGENT_TYPES.keys()),
        help="Type of agent to run",
    )
    
    parser.add_argument(
        "prompt",
        help="Question or command to pass to the agent",
    )
    
    parser.add_argument(
        "--user-id",
        default=os.getenv("LANGFUSE_USER_ID", "local-user"),
        help="User ID to record in Langfuse trace (default: from LANGFUSE_USER_ID env var or local-user)",
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available agent types",
    )
    
    return parser.parse_args()


def list_agents() -> None:
    """Print available agent types and their descriptions."""
    print("\nAvailable agent types:\n")
    for key, info in AGENT_TYPES.items():
        print(f"  {key:15} - {info['name']}")
        print(f"  {' ' * 15}   {info['description']}\n")


def main() -> None:
    """Main entry point for the unified agent runner."""
    args = parse_args()
    
    if args.list:
        list_agents()
        return
    
    agent_info = AGENT_TYPES[args.agent_type]
    logger.info(
        "Running %s... (User: %s)", 
        agent_info["name"], 
        args.user_id
    )
    
    try:
        response = agent_info["runner"](args.prompt, args.user_id)
        print("\n" + "="*80)
        print("Response:")
        print("="*80)
        print(response)
        print("="*80 + "\n")
    except Exception as e:
        logger.error("Error running %s: %s", agent_info["name"], e)
        sys.exit(1)


if __name__ == "__main__":
    main()

