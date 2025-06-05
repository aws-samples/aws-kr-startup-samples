from fastapi import FastAPI, Request, HTTPException, Depends
from mcp.server.sse import SseServerTransport
from starlette.routing import Mount
from weather import mcp
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
from starlette.websockets import WebSocketDisconnect
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format='[%(asctime)s] %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%m/%d/%y %H:%M:%S',
)

# Load environment variables
load_dotenv()

# Cognito configuration
COGNITO_POOL_ID = os.getenv('COGNITO_POOL_ID', 'your-region_YourPoolId')
COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID', 'your-client-id-value')
COGNITO_REGION = os.getenv('COGNITO_REGION', 'your-region')

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name=COGNITO_REGION)

# Create FastAPI application with metadata
app = FastAPI(
    title="FastAPI MCP SSE",
    description="A demonstration of Server-Sent Events with Model Context "
    "Protocol integration and Cognito authentication",
    version="0.1.0",
)

sse = SseServerTransport("/messages/")

app.router.routes.append(Mount("/messages", app=sse.handle_post_message))

@app.get("/messages", tags=["MCP"], include_in_schema=True)
def messages_docs():
    """
    Messages endpoint for SSE communication

    This endpoint is used for posting messages to SSE clients.
    Note: This route is for documentation purposes only.
    The actual implementation is handled by the SSE transport.
    """
    pass

async def verify_token(request: Request):
    """Verify Cognito token from request headers"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.error("Missing or invalid authorization header")
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid authorization header"
            )
        
        token = auth_header.split(' ')[1]
        logger.info("Verifying token with Cognito")
        
        # Verify the token with Cognito
        response = cognito_client.get_user(
            AccessToken=token
        )
        logger.info(f"Token verified for user: {response['Username']}")
        return response
    except ClientError as e:
        logger.error(f"Cognito verification failed: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )

@app.get("/sse", tags=["MCP"])
async def handle_sse(request: Request):
    """
    SSE endpoint that connects to the MCP server

    This endpoint establishes a Server-Sent Events connection with the client
    and forwards communication to the Model Context Protocol server.
    Requires valid Cognito authentication via Authorization header.
    """
    try:
        # Verify authentication before establishing SSE connection
        user = await verify_token(request)
        logger.info(f"Authentication successful for user: {user['Username']}")
        
        async with sse.connect_sse(request.scope, request.receive, request._send) as (
            read_stream,
            write_stream,
        ):
            logger.info("SSE connection established")
            await mcp._mcp_server.run(
                read_stream,
                write_stream,
                mcp._mcp_server.create_initialization_options(),
            )
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except HTTPException as e:
        logger.error(f"Authentication error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error in SSE connection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

import routes  # noqa