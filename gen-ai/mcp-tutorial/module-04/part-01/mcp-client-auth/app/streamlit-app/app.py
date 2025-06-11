import streamlit as st
import asyncio
from client import MCPClient
import os
from dotenv import load_dotenv
import logging
import json

# Configure logging
logging.basicConfig(
    format='[%(asctime)s] %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%m/%d/%y %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

async def authenticate_user(username: str, password: str):
    """Authenticate user with Cognito"""
    try:
        client = MCPClient()
        if await client.authenticate_with_cognito(username, password):
            st.session_state.access_token = client.access_token
            st.session_state.authenticated = True
            return True
        return False
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return False

async def process_query(query: str, server_url: str):
    """Process user query through MCP client with a new connection"""
    client = None
    try:
        if not st.session_state.authenticated or not st.session_state.access_token:
            raise Exception("Not authenticated. Please log in again.")

        # Create new client for this query
        client = MCPClient()
        client.access_token = st.session_state.access_token
        
        # Connect to server
        tools = await client.connect_to_server(server_url)
        if not tools:
            raise Exception("Failed to connect to server")
            
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": query})
        
        # Process query
        messages = await client.invoke_agent(query, thread_id=42)
        
        # Format and add assistant's response
        if isinstance(messages, list):
            final_response = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_response,
                "raw_messages": messages
            })
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": str(messages),
                "raw_messages": messages
            })
        return True
    except Exception as e:
        error_msg = str(e)
        if "NoneType" in error_msg and "ainvoke" in error_msg:
            error_msg = "Connection to server lost. Please try again."
        logger.error(f"Query processing error: {error_msg}")
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Error: {error_msg}",
            "error": True
        })
        return False
    finally:
        # Clean up client resources
        if client:
            try:
                await client.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")

def display_message(message):
    """Display a chat message with optional expandable details"""
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        # Add expandable section for raw messages if available
        if "raw_messages" in message and message["raw_messages"]:
            with st.expander("View Details"):
                st.json(message["raw_messages"])
        
        # Show error styling if there was an error
        if message.get("error"):
            st.error("An error occurred while processing your request")

def main():
    st.set_page_config(page_title="MCP Chat Application", layout="wide")
    st.title("MCP Chat Application")
    
    # Server URL configuration
    with st.sidebar:
        st.header("Server Configuration")
        server_url = st.text_input(
            "Server URL",
            value="http://localhost:8000/sse",
            help="Enter the MCP server URL (must end with /sse)"
        )
        
        if not server_url.endswith("/sse"):
            st.warning("Server URL must end with /sse")
            server_url = server_url.rstrip("/") + "/sse"

    if not st.session_state.authenticated:
        # Login form
        st.header("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                if username and password:
                    with st.spinner("Authenticating..."):
                        if asyncio.run(authenticate_user(username, password)):
                            st.success("Authentication successful!")
                            st.rerun()
                        else:
                            st.error("Authentication failed. Please check your credentials.")
                else:
                    st.warning("Please enter both username and password.")
    else:
        # Chat interface
        st.header("Chat")
        
        # Display chat messages
        for message in st.session_state.messages:
            display_message(message)

        # Chat input
        if prompt := st.chat_input("What would you like to know?"):
            with st.spinner("Processing your request..."):
                if asyncio.run(process_query(prompt, server_url)):
                    st.rerun()
                else:
                    st.error("Failed to process query")

        # Logout button
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.access_token = None
            st.session_state.messages = []
            st.rerun()

if __name__ == "__main__":
    main()