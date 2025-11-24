from __future__ import annotations

import argparse
import ast
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional, Tuple

from dotenv import load_dotenv
from langfuse import Langfuse, get_client
from strands import Agent, tool
from strands_tools import file_read, python_repl

_CODE_EXEC_TOOL = python_repl
_CODE_EXEC_TOOL_NAME = "python_repl"

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


SERVERS_ROOT = Path(__file__).parent / "servers"


def _extract_summary(file_path: Path) -> str:
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
    """Scan the ./servers tree to map MCP wrappers, with optional filtering and summaries."""
    if not SERVERS_ROOT.exists():
        return "servers 디렉터리가 존재하지 않습니다."

    normalized_detail = detail_level.lower()
    if normalized_detail not in {"name", "summary"}:
        normalized_detail = "name"

    normalized_target = target.lower() if target else None

    lines: List[str] = [f"servers ({SERVERS_ROOT})"]
    matches_found = False

    for child in sorted(SERVERS_ROOT.iterdir()):
        child_lines, child_match = _collect_tree(
            child, depth=0, max_depth=max_depth, detail_level=normalized_detail, target=normalized_target
        )
        if child_lines:
            lines.extend(child_lines)
        matches_found |= child_match

    if not matches_found and normalized_target:
        lines.append(f"(no entries matched '{target}')")

    return "\n".join(lines)


def init_langfuse_client() -> Optional[Langfuse]:
    """Initialise Langfuse if credentials are present."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not (public_key and secret_key):
        logger.warning("Langfuse credentials not found; tracing disabled.")
        return None

    Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    client = get_client()
    logger.info("Langfuse tracing enabled for %s.", host)
    return client


LANGFUSE_CLIENT = init_langfuse_client()


@contextmanager
def traced_run(
    prompt: str, user_id: Optional[str] = None
) -> Generator[Optional[object], None, None]:
    """Wrap an agent run in a Langfuse span if configured."""
    if LANGFUSE_CLIENT is None:
        yield None
        return

    with LANGFUSE_CLIENT.start_as_current_span(
        name="strands-agent-run", input={"prompt": prompt}
    ) as span:
        if user_id:
            LANGFUSE_CLIENT.update_current_trace(user_id=user_id)
        yield span


def execute_agent(prompt: str) -> str:
    """Instantiate the MCP-backed agent and run the prompt."""
    system_prompt = (
        "You operate in a code-execution environment. "
        "For straightforward natural language questions, answer directly. "
        "When the request involves AWS infrastructure, MCP servers, or any task that should use the "
        "Python wrappers under the ./servers directory, follow this playbook:\n"
        "1. Call the `search_tools` Strands tool with an appropriate `target` (service name, tool name, etc.) "
        "and `detail_level=\"summary\"` to locate relevant MCP wrappers.\n"
        "2. Use `file_read` to inspect any promising wrapper files so you understand the function signature and required arguments before invoking them.\n"
        f"3. Import and execute the wrapper (or otherwise call the underlying MCP tool) using the `{_CODE_EXEC_TOOL_NAME}` tool. "
        "Provide required parameters and capture results for the user.\n"
        "4. Only reach for the workflow tool if you have explicitly defined workflows and the user request benefits from orchestrated multi-step execution; otherwise skip workflows.\n"
        "Always explain which wrappers or MCP tools you called and summarize their outputs. "
        "If no MCP interaction is needed, bypass these steps and respond normally."
    )
    agent = Agent(
        tools=[file_read, _CODE_EXEC_TOOL, search_tools],
        system_prompt=system_prompt,
    )
    return agent(prompt)


def run(prompt: str, user_id: Optional[str] = None) -> str:
    """Run the Strands agent and capture traces."""
    logger.info("Starting prompt execution: %s", prompt)
    with traced_run(prompt, user_id) as span:
        response = execute_agent(prompt)
        if span is not None:
            LANGFUSE_CLIENT.update_current_span(output={"response": response})
    logger.info("Prompt execution finished.")
    return response


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Langfuse 추적이 포함된 Strands SDK 예제"
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="What is AWS Lambda?",
        help="에이전트에게 전달할 질문",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("LANGFUSE_USER_ID", "local-user"),
        help="Langfuse trace에 기록할 사용자 ID",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    response = run(args.prompt, args.user_id)
    print(response)


if __name__ == "__main__":
    main()