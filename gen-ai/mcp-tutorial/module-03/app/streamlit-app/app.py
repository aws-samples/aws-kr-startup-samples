import streamlit as st
import asyncio
from client import MCPReActAgent
import nest_asyncio

nest_asyncio.apply()

if "loop" not in st.session_state:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(loop)
    st.session_state.loop = loop

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = None
    st.session_state.connected = False
    st.session_state.tools = None

st.set_page_config(page_title="Streamlit MCP Host", layout="wide")

# side bar
with st.sidebar:
    st.header("Server Setting")
    
    model_id = st.text_input("Model ID", value="amazon.nova-lite-v1:0")
    region_name = st.text_input("AWS Region", value="us-east-1")
    server_url = st.text_input("MCP Server URL", value="")

    if st.button("Connect"):
        if not st.session_state.connected:
            with st.spinner("Connecting to server..."):
                try:

                    agent = MCPReActAgent(model_id=model_id, region_name=region_name)

                    st.session_state.loop.run_until_complete(agent.connect_mcp_server(server_url))

                    st.session_state.agent = agent
                    st.session_state.connected = True
                    st.session_state.tools = agent.mcp_client.tools
                    st.success(f"Successfully connected to server: '{server_url}'")
                    
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")
        else:
            st.info("Already connected to server")

    st.subheader("Available tools")
    if st.session_state.connected:
        for tool in st.session_state.agent.mcp_client.tools:
            with st.expander(f"{tool.name}"):
                st.markdown(f"**description:** {tool.description}")
                
                st.markdown("**arguments:**")
                params = tool.args_schema.get('properties', {})
                required = tool.args_schema.get('required', [])
                
                if params:
                    param_data = []
                    for param_name, param_info in params.items():
                        param_type = param_info.get('type', '')
                        is_required = "✓" if param_name in required else ""
                        param_data.append([param_name, param_type, is_required])
                    
                    st.table({
                        "parameter": [p[0] for p in param_data],
                        "type": [p[1] for p in param_data],
                        "required": [p[2] for p in param_data]
                        })
    else:
        st.warning("Please connected to server")

# chat
st.title("Streamlit MCP Host")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Input message..."):
    if not st.session_state.connected:
        st.error("You have to connect server first.")
    else:
        with st.chat_message("user"):
            st.write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):

            response_placeholder = st.empty()
            try:
            
                messages = st.session_state.loop.run_until_complete(st.session_state.agent.invoke_agent(prompt))
                
                with st.expander('full messages'):
                    st.markdown(messages)

                final_message = messages[-1].content.split("</thinking>")[-1]
                response_placeholder.markdown(final_message)
                                    
                st.session_state.messages.append({"role": "assistant", "content": final_message})
                
            except Exception as e:
                st.error(f"Response failed: {str(e)}")