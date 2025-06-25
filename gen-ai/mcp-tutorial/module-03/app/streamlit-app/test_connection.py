#!/usr/bin/env python3
"""
Simple script to test MCP server connectivity
"""
import asyncio
import aiohttp
import sys

async def test_http_connection(url: str):
    """Test basic HTTP connectivity"""
    print(f"Testing HTTP connection to: {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}health") as response:
                print(f"Health check status: {response.status}")
                text = await response.text()
                print(f"Health check response: {text}")
                return response.status == 200
    except Exception as e:
        print(f"HTTP connection failed: {e}")
        return False

async def test_mcp_connection(url: str):
    """Test MCP streamable HTTP connection"""
    print(f"\nTesting MCP connection to: {url}")
    
    try:
        from mcp.client.streamable_http import streamablehttp_client
        from mcp import ClientSession
        
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("MCP connection successful!")
                
                # List available tools
                from langchain_mcp_adapters.tools import load_mcp_tools
                tools = await load_mcp_tools(session)
                print(f"Available tools: {[tool.name for tool in tools]}")
                return True
                
    except Exception as e:
        print(f"MCP connection failed: {e}")
        return False

async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_connection.py <server_url>")
        print("Example: python test_connection.py http://localhost:8000/")
        sys.exit(1)
    
    url = sys.argv[1]
    if not url.endswith('/'):
        url += '/'
        print(f"Added trailing slash: {url}")
    
    print("=== MCP Server Connection Test ===")
    
    # Test basic HTTP first
    http_ok = await test_http_connection(url)
    
    if http_ok:
        # Test MCP connection
        mcp_ok = await test_mcp_connection(url)
        
        if mcp_ok:
            print("\n✅ All tests passed! Server is ready for MCP connections.")
        else:
            print("\n❌ MCP connection failed, but HTTP works. Check MCP server implementation.")
    else:
        print("\n❌ Basic HTTP connection failed. Check if server is running and URL is correct.")

if __name__ == "__main__":
    asyncio.run(main())