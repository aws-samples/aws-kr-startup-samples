"""Streamlit app for the dashboard agent."""
import os
import asyncio
import streamlit as st
import sys
import atexit

from dashboard_agent.dashboard_agent import DashboardAgent
from dashboard_agent.settings import get_default_settings
# from dashboard_agent.aws_mcp_tools import initialize_mcp_clients, cleanup_mcp_clients

def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        # Get settings
        settings = get_default_settings()
        os.environ['AWS_REGION'] = settings.bedrock.region
        
        # Initialize MCP clients (commented out - aws_mcp_tools module not found)
        # if "mcp_initialized" not in st.session_state:
        #     try:
        #         initialize_mcp_clients()
        #         st.session_state.mcp_initialized = True
        #         # Register cleanup function to run on app exit
        #         atexit.register(cleanup_mcp_clients)
        #     except Exception as e:
        #         st.error(f"Failed to initialize AWS MCP clients: {str(e)}")
        #         return
        
        # Create the dashboard agent
        st.session_state.agent = DashboardAgent(settings=settings)

async def process_message(prompt: str):
    """Process a message and return the response."""
    response = st.session_state.agent.process_message(prompt)
    async for event in response:
        if "data" in event:
            yield event["data"]

def chat_interface():
    """Chat interface for the dashboard agent."""
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("메시지를 입력하세요"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Get agent response
        with st.chat_message("assistant"):
            try:
                response_placeholder = st.empty()
                full_response = ""
                
                # Run async process_message in event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def update_response():
                    nonlocal full_response
                    async for chunk in process_message(prompt):
                        full_response += chunk
                        response_placeholder.markdown(full_response)
                
                loop.run_until_complete(update_response())
                loop.close()
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Error: {str(e)}")

def main():
    """Main function to run the Streamlit app."""
    try:
        # Initialize session state
        initialize_session_state()
        
        # Chat Interface
        chat_interface()
    except KeyboardInterrupt:
        # Handle graceful shutdown
        # cleanup_mcp_clients()
        st.stop()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        # cleanup_mcp_clients()

if __name__ == "__main__":
    main() 