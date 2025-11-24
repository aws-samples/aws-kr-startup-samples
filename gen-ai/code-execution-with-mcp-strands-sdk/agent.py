from __future__ import annotations

import argparse
import logging
import os
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Generator, List, Optional

from dotenv import load_dotenv
from langfuse import Langfuse, get_client
from mcp import StdioServerParameters, stdio_client
from strands import Agent
from strands.tools.mcp import MCPClient, MCPAgentTool
from strands.types.collections import PaginatedList

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]

    def parameters(self) -> StdioServerParameters:
        return StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env if self.env else None,
        )


def _default_log_file(filename: str) -> str:
    return str(Path(__file__).with_name(filename))


MCP_SERVERS: tuple[MCPServerConfig, ...] = (
    MCPServerConfig(
        name="aws-documentation",
        command="uvx",
        args=["awslabs.aws-documentation-mcp-server@latest"],
        env={"FASTMCP_LOG_LEVEL": os.getenv("AWS_DOCS_MCP_LOG_LEVEL", "ERROR")},
    ),
    MCPServerConfig(
        name="amazon-eks",
        command="uvx",
        args=[
            "awslabs.eks-mcp-server@latest",
            "--allow-write",
            "--allow-sensitive-data-access",
        ],
        env={"FASTMCP_LOG_LEVEL": os.getenv("EKS_MCP_LOG_LEVEL", "ERROR")},
    ),
    MCPServerConfig(
        name="amazon-ecs",
        command="uvx",
        args=["--from", "awslabs-ecs-mcp-server", "ecs-mcp-server"],
        env={
            "FASTMCP_LOG_LEVEL": os.getenv("ECS_MCP_LOG_LEVEL", "ERROR"),
            "FASTMCP_LOG_FILE": os.getenv(
                "ECS_MCP_LOG_FILE", _default_log_file("ecs-mcp-server.log")
            ),
            "ALLOW_WRITE": os.getenv("ECS_MCP_ALLOW_WRITE", "false"),
            "ALLOW_SENSITIVE_DATA": os.getenv(
                "ECS_MCP_ALLOW_SENSITIVE_DATA", "false"
            ),
        },
    ),
    MCPServerConfig(
        name="aws-cdk",
        command="uvx",
        args=["awslabs.cdk-mcp-server@latest"],
        env={"FASTMCP_LOG_LEVEL": os.getenv("CDK_MCP_LOG_LEVEL", "ERROR")},
    ),
)


def build_mcp_clients() -> list[MCPClient]:
    clients: list[MCPClient] = []
    for config in MCP_SERVERS:
        parameters = config.parameters()
        client = MCPClient(lambda params=parameters: stdio_client(params))
        clients.append(client)
    return clients


def list_all_tools(client: MCPClient) -> list[MCPAgentTool]:
    tools: list[MCPAgentTool] = []
    pagination_token: Optional[str] = None
    while True:
        page: PaginatedList[MCPAgentTool] = client.list_tools_sync(pagination_token)
        tools.extend(page)
        if page.pagination_token is None:
            break
        pagination_token = page.pagination_token
    return tools


def init_langfuse_client() -> Optional[Langfuse]:
    """Initialise Langfuse if credentials are present."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not (public_key and secret_key):
        logger.warning("Langfuse 환경변수를 찾지 못해 추적을 비활성화했습니다.")
        return None

    Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    client = get_client()
    logger.info("Langfuse 추적이 %s 대상으로 활성화되었습니다.", host)
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
    clients = build_mcp_clients()
    with ExitStack() as stack:
        for client in clients:
            stack.enter_context(client)
        tools: list[MCPAgentTool] = []
        for client in clients:
            tools.extend(list_all_tools(client))
        agent = Agent(tools=tools)
        return agent(prompt)


def run(prompt: str, user_id: Optional[str] = None) -> str:
    """Run the Strands agent and capture traces."""
    logger.info("프롬프트 실행 시작: %s", prompt)
    with traced_run(prompt, user_id) as span:
        response = execute_agent(prompt)
        if span is not None:
            LANGFUSE_CLIENT.update_current_span(output={"response": response})
    logger.info("프롬프트 실행 완료")
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