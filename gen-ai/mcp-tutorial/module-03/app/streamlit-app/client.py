import asyncio
import sys
from contextlib import AsyncExitStack
from typing import Any, List

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_aws import ChatBedrockConverse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('mcp').setLevel(logging.WARNING)
logging.getLogger('langchain_aws').setLevel(logging.WARNING)

class MCPClient:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.tools = []
        self.session = None

    async def connect_to_server(self, server_url: str):
        if not server_url.endswith('/'):
            server_url = f"{server_url}/"

        self.read, self.write, _ = await self.exit_stack.enter_async_context(
            streamablehttp_client(server_url)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.read, self.write)
        )
            
        session = await self.session.initialize()
        self.tools = await load_mcp_tools(self.session)
        self.session = session
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.exit_stack:
            await self.exit_stack.aclose()

class MCPReActAgent:
    def __init__(self, model_id: str = "amazon.nova-lite-v1:0", region_name: str = "us-east-1"):
        self.model_id = model_id
        self.region_name = region_name
        self.bedrock = ChatBedrockConverse(
            model_id=self.model_id,
            region_name=self.region_name
        )
        self.mcp_client = MCPClient()

    async def connect_mcp_server(self, server_url: str):
        """Connect to MCP server and retrieve available tools"""
        
        try:

            await self.mcp_client.connect_to_server(server_url)

            print("MCP Server Connected!")
            print("[Available tools]")
            for tool in self.mcp_client.tools:
                print(f"- {tool.name}: {tool.description}")
            
            self.agent = create_react_agent(
                model=self.bedrock,
                tools=self.mcp_client.tools,
                checkpointer=MemorySaver()
            )
            
        except Exception as e:
            raise Exception(f"Failed to connect to MCP server: {e}")
    
    async def invoke_agent(self, query: str, thread_id: int = 42) -> List[Any]:
        """Execute query using the MCP agent"""
        if not self.agent:
            raise RuntimeError("Client not connected to server")
        
        response = await self.agent.ainvoke(
            {"messages": query},
            config={"configurable": {"thread_id": thread_id}}
        )
        return response["messages"]

    async def stream_agent(self, query: str, thread_id: int = 42):
        async for chunk in self.agent.astream(
            {"messages": query},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates"
        ):
            for value in chunk.values():
                value["messages"][-1].pretty_print()
    
    async def chat_loop(self):
        """Interactive chat loop for command-line usage"""
        print("MCP Client Started! Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break                
                await self.stream_agent(query)

            except Exception as e:
                print(f"Error: {e}")

    async def cleanup(self):
        """Cleanup resources"""
        print("clean up")
        await self.mcp_client.cleanup()

async def main():
    """Command-line interface"""
    if len(sys.argv) < 2:
        print("Usage: python client.py <mcp_server_url>")
        sys.exit(1)
    
    agent = MCPReActAgent()
    
    try:
        server_url = sys.argv[1]
        await agent.connect_mcp_server(server_url)
        await agent.chat_loop()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())