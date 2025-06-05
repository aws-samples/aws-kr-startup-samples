from mcp import ClientSession
from mcp.client.sse import sse_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_aws import ChatBedrockConverse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel, Field
from typing import Optional
from contextlib import AsyncExitStack
import boto3
from botocore.exceptions import ClientError

import logging
import sys
import asyncio
import os
from dotenv import load_dotenv
import hashlib
import hmac
import base64

# Load environment variables
load_dotenv()

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
    
    # Initialize Cognito client with environment variables
    self.cognito_region = os.getenv('COGNITO_REGION', 'your-region')
    self.cognito_client = boto3.client('cognito-idp', region_name=self.cognito_region)
    self.cognito_pool_id = os.getenv('COGNITO_POOL_ID', 'your-region_YourPoolId')
    self.cognito_client_id = os.getenv('COGNITO_CLIENT_ID', 'your-client-id-value')
    self.cognito_client_secret = os.getenv('COGNITO_CLIENT_SECRET', 'your-client-secret-value')

    if not all([self.cognito_pool_id, self.cognito_client_id]):
        raise ValueError("Missing required Cognito configuration. Please set COGNITO_POOL_ID and COGNITO_CLIENT_ID environment variables.")
    
    self.access_token = None

  def _calculate_secret_hash(self, username: str) -> str:
    """Calculate SECRET_HASH for Cognito authentication"""
    if not self.cognito_client_secret:
        return None
            
    message = username + self.cognito_client_id
    dig = hmac.new(
        self.cognito_client_secret.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

  async def authenticate_with_cognito(self, username: str, password: str):
    """Authenticate with Cognito and get access token"""
    try:
      auth_params = {
        'USERNAME': username,
        'PASSWORD': password
      }
      
      # Calculate and add SECRET_HASH if client secret exists
      secret_hash = self._calculate_secret_hash(username)
      if secret_hash:
        auth_params['SECRET_HASH'] = secret_hash

      response = self.cognito_client.initiate_auth(
        ClientId=self.cognito_client_id,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters=auth_params
      )
      
      self.access_token = response['AuthenticationResult']['AccessToken']
      logger.info("Successfully authenticated with Cognito")
      return True
    except ClientError as e:
      logger.error(f"Authentication failed: {str(e)}")
      if 'UserNotFoundException' in str(e):
        logger.error("User not found. Please check your username.")
      elif 'NotAuthorizedException' in str(e):
        logger.error("Invalid password or authentication failed.")
      elif 'ResourceNotFoundException' in str(e):
        logger.error("Cognito User Pool or Client not found. Please check your Cognito configuration.")
      return False
    except Exception as e:
      logger.error(f"Unexpected error during authentication: {str(e)}")
      return False

  async def connect_to_server(self, server_url: str):
    if not self.access_token:
      raise Exception("Not authenticated. Please call authenticate_with_cognito first.")

    # Add authorization header to the SSE connection
    headers = {
      "Authorization": f"Bearer {self.access_token}"
    }
    
    self.read, self.write = await self.exit_stack.enter_async_context(
      sse_client(server_url, headers=headers)
    )
    self.session = await self.exit_stack.enter_async_context(ClientSession(self.read, self.write))

    await self.session.initialize()

    tools = await load_mcp_tools(self.session)    
    logger.info("Connected to server with tools: %s", [tool.name for tool in tools])

    self.agent = create_react_agent(model=self.bedrock, tools=tools, checkpointer=MemorySaver())

    return tools
  
  async def invoke_agent(self, query: str, thread_id: int):
    """Invoke the agent with a query and return the messages"""
    try:
        response = await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": query}]},
            config={"configurable": {"thread_id": thread_id}}
        )
        
        # Extract messages from the response
        if isinstance(response, dict) and "messages" in response:
            return response["messages"]
        elif isinstance(response, list):
            return response
        else:
            logger.warning(f"Unexpected response format: {response}")
            return [{"role": "assistant", "content": str(response)}]
            
    except Exception as e:
        logger.error(f"Error in invoke_agent: {str(e)}")
        raise

  async def chat_loop(self):
    """Interactive chat loop for command line interface"""
    logger.info("MCP Client Started!")
    logger.info("Type your queries or 'quit' to exit.")

    while True:
        try:
            query = input("\nQuery: ").strip()

            if query.lower() == 'quit':
                break

            messages = await self.invoke_agent(query, thread_id=42)
            if isinstance(messages, list):
                # Print the last message's content
                last_message = messages[-1]
                if isinstance(last_message, dict) and "content" in last_message:
                    logger.info(last_message["content"])
                else:
                    logger.info(str(last_message))
            else:
                logger.info(str(messages))

        except Exception as e:
            logger.error(f"Error in chat loop: {str(e)}")

  async def cleanup(self):
      if self.exit_stack:
          await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 3:
        logger.info("Usage: python client.py <mcp server url> <username> <password>")
        sys.exit(1)

    client = MCPClient()
    try:
        server_path = sys.argv[1]
        username = sys.argv[2]
        password = sys.argv[3]

        # Authenticate with Cognito first
        if not await client.authenticate_with_cognito(username, password):
            logger.error("Authentication failed. Exiting...")
            sys.exit(1)

        logger.info("Connecting to '%s'", server_path)
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