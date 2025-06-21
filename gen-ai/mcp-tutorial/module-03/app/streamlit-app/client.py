from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_aws import ChatBedrockConverse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel, Field
from typing import Optional
import contextlib

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
        self.server_url = None
        self.tools = None
        self.bedrock = ChatBedrockConverse(
            model_id=model_id,
            region_name=region_name
        )
        self.agent = None

    async def connect_to_server(self, server_url: str):
        """Store connection info and test connectivity"""
        # Ensure URL ends with /
        if not server_url.endswith('/'):
            server_url += '/'
            
        self.server_url = server_url
        logger.info(f"Attempting to connect to: {server_url}")

        try:
            # Test connection and get tools
            async with streamablehttp_client(server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    logger.info("Initializing MCP session...")
                    await session.initialize()
                    logger.info("Session initialized successfully")
                    
                    logger.info("Loading MCP tools...")
                    tools = await load_mcp_tools(session)
                    logger.info("Connected to server with tools: %s", [tool.name for tool in tools])
                    
                    # Store tools and create agent
                    self.tools = tools
                    self.agent = create_react_agent(model=self.bedrock, tools=tools, checkpointer=MemorySaver())
                    
                    return tools
        except Exception as e:
            logger.error(f"Detailed connection error: {type(e).__name__}: {str(e)}")
            
            # Handle ExceptionGroup (Python 3.11+)
            if hasattr(e, 'exceptions'):
                logger.error("Exception details:")
                for i, exc in enumerate(e.exceptions):
                    logger.error(f"  Exception {i+1}: {type(exc).__name__}: {exc}")
            
            # Extract root cause from nested exceptions
            root_error = e
            while hasattr(root_error, '__cause__') and root_error.__cause__:
                root_error = root_error.__cause__
            while hasattr(root_error, 'exceptions') and root_error.exceptions:
                root_error = root_error.exceptions[0]
            
            logger.error(f"Root cause: {type(root_error).__name__}: {root_error}")
            
            # Check if it's a connection error
            error_msg = str(root_error).lower()
            if any(keyword in error_msg for keyword in ['connection', 'connect', 'refused', 'timeout', 'unreachable']):
                raise ConnectionError(f"Cannot connect to MCP server at {server_url}. Please check:\n"
                                    f"1. Server is running and accessible\n"
                                    f"2. URL is correct (should end with /)\n"
                                    f"3. Port is open and not blocked by firewall\n"
                                    f"4. If using AWS ALB, check target group health\n"
                                    f"Root cause: {root_error}")
            else:
                raise Exception(f"MCP connection failed: {root_error}") from e

    async def invoke_agent(self, query: str, thread_id: int):
        """Create new connection for each request to avoid session issues"""
        if not self.server_url or not self.agent:
            raise RuntimeError("Client not connected to server")
            
        # Create fresh connection for this request
        async with streamablehttp_client(self.server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Reload tools with current session
                tools = await load_mcp_tools(session)
                
                # Create temporary agent with fresh tools
                temp_agent = create_react_agent(model=self.bedrock, tools=tools, checkpointer=MemorySaver())
                
                # Execute the query
                response = await temp_agent.ainvoke({"messages": query}, config={"configurable": {"thread_id": thread_id}})
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

                response = await self.invoke_agent(query, thread_id=42)
                logger.info(response[-1].content)

            except Exception as e:
                logger.error(str(e))

    async def cleanup(self):
        """No explicit cleanup needed with this approach"""
        pass

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