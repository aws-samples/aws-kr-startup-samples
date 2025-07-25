"""Streamlit app for the observability agent."""
import asyncio
import streamlit as st
from observability_agent.agents.coordinator import CoordinatorAgent


def initialize_coordinator() -> CoordinatorAgent:
    """Initialize the coordinator agent."""
    coordinator = CoordinatorAgent()
    coordinator.initialize()
    return coordinator


def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "coordinator" not in st.session_state:
        try:
            with st.spinner("Initializing Observability Agent..."):
                st.write("Initializing ToolRegistry...")
                coordinator = initialize_coordinator()
                st.session_state.coordinator = coordinator
                st.write("ToolRegistry initialized successfully.")
                
                # Add datasource greeting as first message
                greeting = coordinator.get_datasource_greeting()
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": greeting
                })
                
                st.success("Observability Agent initialized successfully!")
                st.session_state.initialization_failed = False
                
        except Exception as e:
            st.error(f"💥 INITIALIZATION FAILED: {str(e)}")
            st.error("The observability assistant cannot start due to MCP server connection failures.")
            
            # Show helpful information
            st.info("""
            **Please check:**
            1. MCP server URLs in your .env file are correct
            2. MCP servers are running and accessible  
            3. Network connectivity to the MCP servers
            
            **To retry:** Refresh this page or click the 'Reinitialize Agent' button below.
            """)
            
            st.session_state.coordinator = None
            st.session_state.initialization_failed = True


async def process_message(coordinator: CoordinatorAgent, prompt: str):
    """Process a message and return the response."""
    try:
        agent = coordinator.get_agent()
        result = agent.stream_async(prompt)
        async for event in result:
            if "data" in event:
                yield event["data"]
    except Exception as e:
        yield f"Error processing message: {str(e)}"


def cleanup_coordinator():
    """Clean up the coordinator and its resources."""
    if "coordinator" in st.session_state and st.session_state.coordinator is not None:
        try:
            st.session_state.coordinator.cleanup()
        except Exception as e:
            st.error(f"Error cleaning up coordinator: {str(e)}")
        finally:
            st.session_state.coordinator = None


def chat_interface():
    """Chat interface for the observability agent."""
    # Check if initialization failed
    if st.session_state.get("initialization_failed", False):
        st.warning("⚠️ The observability agent is not available due to initialization failures.")
        
        # Provide retry option
        if st.button("🔄 Retry Initialization", help="Attempt to reinitialize the agent"):
            # Clear the failed state and retry
            if "coordinator" in st.session_state:
                del st.session_state.coordinator
            if "initialization_failed" in st.session_state:
                del st.session_state.initialization_failed
            st.rerun()
        
        return  # Don't show chat interface
    
    # Add a button to reinitialize the agent if needed
    if st.button("Reinitialize Agent", help="Click if the agent is not responding"):
        cleanup_coordinator()
        initialize_session_state()
        st.rerun()
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Enter your observability query..."):
        # Check if coordinator is available
        if st.session_state.coordinator is None:
            st.error("Agent not initialized. Please click 'Retry Initialization' button.")
            return
            
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Get agent response
        with st.chat_message("assistant"):
            try:
                response_placeholder = st.empty()
                full_response = ""
                
                # Run async process_message
                async def update_response():
                    nonlocal full_response
                    async for chunk in process_message(st.session_state.coordinator, prompt):
                        full_response += chunk
                        response_placeholder.markdown(full_response)
                
                asyncio.run(update_response())
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Error: {str(e)}")


def main():
    """Main function to run the Streamlit app."""
    st.title("🔍 Observability Assistant")
    st.caption("AI-powered agent for analyzing traces, logs, and metrics")
    
    # Initialize session state
    initialize_session_state()
    
    # Chat Interface
    chat_interface()
    
    # Cleanup on app termination (this won't always work with Streamlit)
    import atexit
    atexit.register(cleanup_coordinator)


if __name__ == "__main__":
    main() 