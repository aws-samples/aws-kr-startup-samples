# Create server parameters for stdio connection
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from typing import Optional
from contextlib import AsyncExitStack

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_aws import ChatBedrockConverse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
import logging

import asyncio

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(
    format='[%(asctime)s] %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%m/%d/%y %H:%M:%S',
)

class MCPClient:
  def __init__(self, model_id="us.amazon.nova-lite-v1:0", region_name="us-east-1"):
    self.session: Optional[ClientSession] = None
    self.exit_stack = AsyncExitStack()
    self.bedrock = ChatBedrockConverse(
        model_id=model_id,
        region_name=region_name
    )
    self.agent = None

  async def connect_to_server(self, server_script_path: str):
    """Connect to an MCP server

    Args:
        server_script_path: Path to the server script (.py or .js)
    """
    is_python = server_script_path.endswith('.py')
    is_js = server_script_path.endswith('.js')
    if not (is_python or is_js):
        raise ValueError("Server script must be a .py or .js file")

    command = "python" if is_python else "node"
    server_params = StdioServerParameters(
        command=command,
        args=[server_script_path],
        env=None
    )

    stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
    self.stdio, self.write = stdio_transport
    self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

    await self.session.initialize()

    # List available tools
    tools = await load_mcp_tools(self.session)
    logger.info("Connected to server with tools: %s", [tool.name for tool in tools])

    self.agent = create_react_agent(model=self.bedrock, tools=tools, checkpointer=MemorySaver())

    return tools
  
  async def invoke_agent(self, query: str, thread_id: int):
    response = await self.agent.ainvoke({"messages": query}, config={"configurable": {"thread_id": thread_id}})
    
    return response


  async def chat_loop(self):
    """Run an interactive chat loop"""
    logger.info("MCP Client Started!")
    logger.info("Type your queries or 'quit' to exit.")

    while True:
        try:
            query = input("\nQuery: ").strip()

            if query.lower() == 'quit':
                break

            response = await self.invoke_agent(query)
            logger.info(response)

        except Exception as e:
            logger.error("\nError: %s", str(e))

  async def cleanup(self):
      """Clean up resources"""
      if self.exit_stack:
          await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        logger.info("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        # 서버에 연결
        server_path = sys.argv[1]
        logger.info("서버 '%s'에 연결 중...", server_path)
        tools = await client.connect_to_server(server_path)
        logger.info("사용 가능한 도구: %s개", len(tools))
        
        # 대화형 루프 시작
        await client.chat_loop()
    except Exception as e:
        logger.error("오류 발생: %s", str(e))
    finally:
        # 항상 리소스 정리
        logger.info("리소스 정리 중...")
        await client.cleanup()
        logger.info("종료되었습니다.")

if __name__ == "__main__":
    import sys
        
    # 메인 함수 실행
    asyncio.run(main())
