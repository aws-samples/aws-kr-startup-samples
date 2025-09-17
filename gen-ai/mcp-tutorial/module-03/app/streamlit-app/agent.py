from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from strands.tools.mcp.mcp_types import MCPTransport

from contextlib import ExitStack
from typing import List
import json
import sys
import asyncio

class MCPAgent:
  def __init__(self, model_id="us.amazon.nova-lite-v1:0", region_name="us-east-1", system_prompt=None):
    self.model_id = model_id
    self.region_name = region_name
    self.clients: List[MCPTransport] = []
    self.tools = []
    self.system_prompt = system_prompt
    self.messages = []

  def connect_to_server(self, url):
    mcp_client = MCPClient(lambda: streamablehttp_client(url))
    self.clients.append(mcp_client)

    with mcp_client:
       tools = mcp_client.list_tools_sync()
       self.tools.extend(tools)

  def invoke(self, query):

    with ExitStack() as stack:
      for client in self.clients:
          stack.enter_context(client)

      agent = Agent(
        model=BedrockModel(model_id=self.model_id, region_name=self.region_name),
        system_prompt=self.system_prompt,
        tools=self.tools,
        messages=self.messages,
        callback_handler=None
      )

      response = agent(query)
      self.messages = agent.messages

      return response.message["content"]
    
  async def stream(self, query):
    with ExitStack() as stack:
      for client in self.clients:
          stack.enter_context(client)

      agent = Agent(
        model=BedrockModel(model_id=self.model_id, region_name=self.region_name),
        system_prompt=self.system_prompt,
        tools=self.tools,
        messages=self.messages,
        callback_handler=None
      )

      tool_id = None

      async for chunk in agent.stream_async(query):

        if "current_tool_use" in chunk and chunk["current_tool_use"].get("name"):
            if tool_id == None: 
                tool_id = chunk["current_tool_use"]["toolUseId"]
                yield f"\n\n **{chunk['current_tool_use']['name']} ({tool_id})** 도구를 호출합니다. \n\n ```json\n"

            try:
              tool_input = chunk['delta']['toolUse']["input"]
              if(len(tool_input) > 0 and tool_input[-1] == "}"):
                yield f"{json.dumps(json.loads(chunk['current_tool_use']['input']), indent=2)}"
            except:
               print(chunk)


        if "data" in chunk:
            if tool_id != None:
                tool_id = None
                yield "\n```\n **도구 호출 결과** \n"

                yield f"""```json
                {json.dumps(agent.messages[-1]['content'][0], indent=2)}
``` \n """

            yield chunk["data"]


  async def chat_loop(self):
    print("MCP Client Started! Type your queries or 'quit' to exit.")
    
    while True:
      try:
        query = input("\nQuery: ").strip()
        if query.lower() == 'quit':
            break                
        async for chunk in self.stream(query):
           print(chunk, end="")

      except Exception as e:
        print(f"Error: {e}")

async def main():
    """Command-line interface"""
    if len(sys.argv) < 2:
        print("Usage: python client.py <mcp_server_url>")
        sys.exit(1)
    
    agent = MCPAgent()
    
    try:
        server_url = sys.argv[1]
        agent.connect_to_server(server_url)
        await agent.chat_loop()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())