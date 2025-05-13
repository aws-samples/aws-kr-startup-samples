from mcp import ClientSession
from mcp.client.sse import sse_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_aws import ChatBedrockConverse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel, Field
from typing import Optional
from contextlib import AsyncExitStack

import logging
import sys
import asyncio

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='[%(asctime)s] %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%m/%d/%y %H:%M:%S',
)

class MCPClient:
  def __init__(self, model_id="amazon.nova-lite-v1:0", region_name="us-east-1"):
    self.session: Optional[ClientSession] = None
    self.exit_stack = AsyncExitStack()
    self.bedrock = ChatBedrockConverse(
        model_id=model_id,
        region_name=region_name
    )
    self.agent = None

  async def connect_to_server(self, server_url: str):

    self.read, self.write = await self.exit_stack.enter_async_context(sse_client(server_url))
    self.session = await self.exit_stack.enter_async_context(ClientSession(self.read, self.write))

    await self.session.initialize()

    tools = await load_mcp_tools(self.session)    
    logger.info("Connected to server with tools: %s", [tool.name for tool in tools])

    self.agent = create_react_agent(model=self.bedrock, tools=tools, checkpointer=MemorySaver())

    return tools
  
  async def invoke_agent(self, query: str, thread_id: int):
    response = await self.agent.ainvoke({"messages": query}, config={"configurable": {"thread_id": thread_id}})
    messages = response["messages"]
    
    return messages


  async def chat_loop(self):
    logger.info("MCP Client Started!")
    logger.info("Type your queries or 'quit' to exit.")

    while True:
        try:
            query = input("\nQuery: ").strip()

            if query.lower() == 'quit':
                break

            _, response = await self.invoke_agent(query, thread_id=42)
            logger.info(response)

        except Exception as e:
            logger.error(str(e))

  async def cleanup(self):
      if self.exit_stack:
          await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        logger.info("Usage: python client.py <mcp server url>")
        sys.exit(1)

    client = MCPClient()
    try:
        server_path = sys.argv[1]
        logger.info("Connetction to '%s'", server_path)
        await client.connect_to_server(server_path)
        await client.chat_loop()

    except Exception as e:
        logger.error("Error: %s", str(e))
    finally:
        logger.info("Cleaning up resource")
        await client.cleanup()
        logger.info("Terminated")

if __name__ == "__main__":
    asyncio.run(main())