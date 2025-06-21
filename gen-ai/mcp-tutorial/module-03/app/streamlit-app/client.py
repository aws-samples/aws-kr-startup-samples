from abc import ABC, abstractmethod
from typing import Any, List, Optional, Protocol
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_aws import ChatBedrockConverse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent


# Protocols for Interface Segregation Principle
class MCPConnector(Protocol):
    async def connect_and_get_tools(self, url: str) -> List[Any]: ...

class AgentExecutor(Protocol):
    async def execute_query(self, query: str, thread_id: int) -> List[Any]: ...

class ExceptionHandler(Protocol):
    def extract_root_error(self, error: Exception) -> Exception: ...
    def is_connection_error(self, error: Exception) -> bool: ...


# Single Responsibility Principle: Each class has one reason to change
class URLNormalizer:
    """Responsible for URL formatting"""
    
    @staticmethod
    def normalize(url: str) -> str:
        return url if url.endswith('/') else f"{url}/"


class StreamableHTTPConnector:
    """Responsible for MCP connection and tool loading"""
    
    async def connect_and_get_tools(self, url: str) -> List[Any]:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await load_mcp_tools(session)


class BedrockAgentExecutor:
    """Responsible for executing queries with Bedrock agent"""
    
    def __init__(self, model_id: str, region_name: str, connector: MCPConnector):
        self.bedrock = ChatBedrockConverse(
            model_id=model_id,
            region_name=region_name
        )
        self.connector = connector
    
    async def execute_query(self, server_url: str, query: str, thread_id: int) -> List[Any]:
        tools = await self.connector.connect_and_get_tools(server_url)
        agent = create_react_agent(
            model=self.bedrock, 
            tools=tools, 
            checkpointer=MemorySaver()
        )
        
        response = await agent.ainvoke(
            {"messages": query}, 
            config={"configurable": {"thread_id": thread_id}}
        )
        return response["messages"]


class MCPExceptionHandler:
    """Responsible for exception handling and error extraction"""
    
    def extract_root_error(self, error: Exception) -> Exception:
        root_error = error
        
        # Handle exception chains
        while hasattr(root_error, '__cause__') and root_error.__cause__:
            root_error = root_error.__cause__
            
        # Handle ExceptionGroup (Python 3.11+)
        while hasattr(root_error, 'exceptions') and root_error.exceptions:
            root_error = root_error.exceptions[0]
            
        return root_error
    
    def is_connection_error(self, error: Exception) -> bool:
        error_msg = str(error).lower()
        connection_keywords = ['connection', 'connect', 'refused', 'timeout', 'unreachable']
        return any(keyword in error_msg for keyword in connection_keywords)


class ConnectionError(Exception):
    """Custom exception for connection failures"""
    pass


class MCPClient:
    """
    Main MCP client following SOLID principles:
    - Single Responsibility: Orchestrate MCP operations
    - Open/Closed: Extensible through dependency injection
    - Liskov Substitution: Components are interchangeable via protocols
    - Interface Segregation: Uses focused protocols
    - Dependency Inversion: Depends on abstractions, not concretions
    """
    
    def __init__(
        self, 
        model_id: str = "amazon.nova-lite-v1:0", 
        region_name: str = "us-east-1",
        connector: Optional[MCPConnector] = None,
        exception_handler: Optional[ExceptionHandler] = None,
        url_normalizer: Optional[URLNormalizer] = None
    ):
        self.server_url: Optional[str] = None
        self.tools: Optional[List[Any]] = None
        
        # Dependency Injection (Dependency Inversion Principle)
        self.connector = connector or StreamableHTTPConnector()
        self.exception_handler = exception_handler or MCPExceptionHandler()
        self.url_normalizer = url_normalizer or URLNormalizer()
        
        # Create agent executor with injected connector
        self.agent_executor = BedrockAgentExecutor(model_id, region_name, self.connector)
    
    async def connect_to_server(self, server_url: str) -> List[Any]:
        """Connect to MCP server and retrieve available tools"""
        self.server_url = self.url_normalizer.normalize(server_url)
        
        try:
            self.tools = await self.connector.connect_and_get_tools(self.server_url)
            return self.tools
            
        except Exception as e:
            root_error = self.exception_handler.extract_root_error(e)
            
            if self.exception_handler.is_connection_error(root_error):
                raise ConnectionError(
                    f"Cannot connect to MCP server at {self.server_url}. "
                    f"Please check server status and URL format. "
                    f"Root cause: {root_error}"
                ) from e
            else:
                raise Exception(f"MCP initialization failed: {root_error}") from e
    
    async def invoke_agent(self, query: str, thread_id: int = 42) -> List[Any]:
        """Execute query using the MCP agent"""
        if not self.server_url:
            raise RuntimeError("Client not connected to server")
        
        return await self.agent_executor.execute_query(
            self.server_url, query, thread_id
        )
    
    async def chat_loop(self):
        """Interactive chat loop for command-line usage"""
        print("MCP Client Started! Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                
                response = await self.invoke_agent(query)
                print(response[-1].content)
                
            except Exception as e:
                print(f"Error: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        pass


# Factory Pattern for easy client creation
class MCPClientFactory:
    """Factory for creating configured MCP clients"""
    
    @staticmethod
    def create_default() -> MCPClient:
        """Create client with default configuration"""
        return MCPClient()
    
    @staticmethod
    def create_with_model(model_id: str, region_name: str = "us-east-1") -> MCPClient:
        """Create client with specific model configuration"""
        return MCPClient(model_id=model_id, region_name=region_name)
    
    @staticmethod
    def create_with_custom_components(
        model_id: str = "amazon.nova-lite-v1:0",
        region_name: str = "us-east-1",
        connector: Optional[MCPConnector] = None,
        exception_handler: Optional[ExceptionHandler] = None
    ) -> MCPClient:
        """Create client with custom components for testing"""
        return MCPClient(
            model_id=model_id,
            region_name=region_name,
            connector=connector,
            exception_handler=exception_handler
        )


async def main():
    """Command-line interface"""
    if len(sys.argv) < 2:
        print("Usage: python client.py <mcp_server_url>")
        sys.exit(1)
    
    client = MCPClientFactory.create_default()
    
    try:
        server_url = sys.argv[1]
        await client.connect_to_server(server_url)
        await client.chat_loop()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())