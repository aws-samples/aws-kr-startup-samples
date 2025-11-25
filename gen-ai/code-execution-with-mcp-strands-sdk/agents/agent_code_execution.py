"""Code Execution Agent - Strands agent with dynamic MCP tool discovery.

This agent applies the Anthropic playbook: use search_tools → file_read → 
wrappers under ./mcp-servers/ → invoke MCP via python_repl. Falls back to 
normal replies when MCP access is unnecessary.
"""

from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv
from strands import Agent, tool
from strands_tools import file_read, python_repl
from strands.models import BedrockModel

from core import LANGFUSE_CLIENT, setup_logging, traced_run

load_dotenv()
logger = setup_logging()

_CODE_EXEC_TOOL = python_repl
_CODE_EXEC_TOOL_NAME = "python_repl"

# Update path to point to mcp-servers
SERVERS_ROOT = Path(__file__).parent.parent / "mcp-servers"


def _extract_summary(file_path: Path) -> str:
    """Extract first line of docstring from a Python file.
    
    Args:
        file_path: Path to Python file.
        
    Returns:
        First line of module or function docstring, or empty string.
    """
    try:
        module = ast.parse(file_path.read_text())
    except Exception:
        return ""

    doc = ast.get_docstring(module)
    if doc:
        return doc.strip().splitlines()[0]

    for node in module.body:
        if isinstance(node, ast.FunctionDef):
            func_doc = ast.get_docstring(node)
            if func_doc:
                return func_doc.strip().splitlines()[0]
    return ""


def _collect_tree(
    path: Path,
    depth: int,
    max_depth: int,
    detail_level: str,
    target: Optional[str],
) -> Tuple[List[str], bool]:
    """Recursively collect directory tree with optional filtering.
    
    Args:
        path: Current path to process.
        depth: Current depth in tree.
        max_depth: Maximum depth to traverse.
        detail_level: "name" or "summary" to include docstrings.
        target: Optional filter string for path matching.
        
    Returns:
        Tuple of (lines list, whether match was found).
    """
    rel_str = str(path.relative_to(SERVERS_ROOT))
    match = target is None or target in rel_str.lower()
    indent = "  " * depth

    if path.is_dir():
        if depth >= max_depth:
            if match:
                return [f"{indent}- {path.name}/"], True
            return [], False

        collected: List[str] = []
        child_matched = False
        for child in sorted(path.iterdir()):
            child_lines, child_has_match = _collect_tree(
                child, depth + 1, max_depth, detail_level, target
            )
            if child_lines:
                collected.extend(child_lines)
            child_matched |= child_has_match

        include_directory = match or child_matched
        if include_directory:
            return [f"{indent}- {path.name}/", *collected], True
        return [], False

    if match:
        label = f"{indent}- {path.name}"
        if detail_level == "summary":
            summary = _extract_summary(path)
            if summary:
                label += f" — {summary}"
        return [label], True
    return [], False


@tool
def search_tools(
    max_depth: int = 3,
    *,
    target: Optional[str] = None,
    detail_level: str = "name",
) -> str:
    """Scan the ./mcp-servers tree to map MCP wrappers.
    
    Args:
        max_depth: Maximum directory depth to traverse.
        target: Optional filter string to match against paths.
        detail_level: "name" for file names only, "summary" to include docstrings.
        
    Returns:
        Formatted tree view of matching tools with usage instructions.
    """
    if not SERVERS_ROOT.exists():
        return "mcp-servers directory does not exist."

    normalized_detail = detail_level.lower()
    if normalized_detail not in {"name", "summary"}:
        normalized_detail = "name"

    normalized_target = target.lower() if target else None

    lines: List[str] = [
        f"mcp-servers directory: {SERVERS_ROOT}",
        "",
        "Available MCP wrapper modules:",
    ]
    matches_found = False

    for child in sorted(SERVERS_ROOT.iterdir()):
        child_lines, child_match = _collect_tree(
            child,
            depth=0,
            max_depth=max_depth,
            detail_level=normalized_detail,
            target=normalized_target,
        )
        if child_lines:
            lines.extend(child_lines)
        matches_found |= child_match

    if not matches_found and normalized_target:
        lines.append(f"(no entries matched '{target}')")
    
    # Add usage instructions
    lines.extend([
        "",
        "USAGE INSTRUCTIONS:",
        "1. Use file_read to read the wrapper file (e.g., 'mcp-servers/aws_documentation/search_documentation.py')",
        "2. In python_repl, add the mcp-servers directory to sys.path, then import and call the function:",
        "   Example:",
        "   import sys",
        f"   sys.path.insert(0, '{SERVERS_ROOT}')",
        "   from aws_documentation.search_documentation import search_documentation",
        "   result = search_documentation('AWS Lambda', limit=5)",
        "   print(result)",
    ])

    return "\n".join(lines)


def execute_agent(prompt: str) -> str:
    """Instantiate the code execution agent and run the prompt.
    
    Args:
        prompt: User query to execute.
        
    Returns:
        Agent response string.
    """
    system_prompt = (
        "You operate in a code-execution environment. "
        "For straightforward natural language questions, answer directly. "
        "When the request involves AWS infrastructure, MCP servers, or any task that should use the "
        "Python wrappers under the ./mcp-servers directory, follow this playbook:\n"
        "1. Call the `search_tools` Strands tool with an appropriate `target` (service name, tool name, etc.) "
        "and `detail_level=\"summary\"` to locate relevant MCP wrappers.\n"
        "2. Use `file_read` to inspect any promising wrapper files so you understand the function signature and required arguments before invoking them.\n"
        f"3. CRITICAL: Import and execute the wrapper using the `{_CODE_EXEC_TOOL_NAME}` tool. "
        "You MUST actually call the wrapper function, not just describe it. Follow these steps:\n"
        "   a. Add the mcp-servers directory to sys.path in python_repl\n"
        "   b. Import the wrapper module (e.g., 'from aws_documentation.search_documentation import search_documentation')\n"
        "   c. Call the function with the required parameters\n"
        "   d. Print or return the result\n"
        "   Example code to run in python_repl:\n"
        "   ```python\n"
        "   import sys\n"
        f"   sys.path.insert(0, '{SERVERS_ROOT}')\n"
        "   from aws_documentation.search_documentation import search_documentation\n"
        "   result = search_documentation('AWS Lambda', limit=5)\n"
        "   print(result)\n"
        "   ```\n"
        "4. Always explain which wrappers or MCP tools you called and summarize their outputs.\n"
        "5. If no MCP interaction is needed, bypass these steps and respond normally.\n"
        "\n"
        "IMPORTANT: After finding tools with search_tools, you MUST actually execute them using python_repl. "
        "Do not just describe what you found - actually call the wrapper functions to get real results."
    )
    agent = Agent(
        model="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        tools=[file_read, _CODE_EXEC_TOOL, search_tools],
        system_prompt=system_prompt,
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
        description="Strands Code Execution Agent with Langfuse tracing"
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
    """Main entry point for the Code Execution Agent."""
    args = parse_args()
    response = run(args.prompt, args.user_id)
    print(response)


if __name__ == "__main__":
    main()

