import streamlit as st
import asyncio
from client import MCPClientFactory

if "messages" not in st.session_state:
    st.session_state.messages = []

if "client" not in st.session_state:
    st.session_state.client = None
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
                    async def connect_async():
                        client = MCPClientFactory.create_with_model(model_id=model_id, region_name=region_name)
                        tools = await client.connect_to_server(server_url)
                        return client, tools

                    client, tools = asyncio.run(connect_async())
                    
                    st.session_state.client = client
                    st.session_state.connected = True
                    st.session_state.tools = tools
                    st.success(f"Successfully connected to server: '{server_url}'")
                    
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")
        else:
            st.info("Already connected to server")

    st.subheader("Available tools")
    if st.session_state.connected:
        for tool in st.session_state.tools:
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
                async def invoke_async():
                    return await st.session_state.client.invoke_agent(prompt, thread_id=42)
                
                messages = asyncio.run(invoke_async())
                
                with st.expander('full messages'):
                    st.markdown(messages)

                final_message = messages[-1].content.split("</thinking>")[-1]
                response_placeholder.markdown(final_message)
                                    
                st.session_state.messages.append({"role": "assistant", "content": final_message})
                
            except Exception as e:
                st.error(f"Response failed: {str(e)}")