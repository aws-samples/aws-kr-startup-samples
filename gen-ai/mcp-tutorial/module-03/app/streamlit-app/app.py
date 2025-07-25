import streamlit as st
from client import MCPAgent

if "agent" not in st.session_state:
    st.session_state.agent = None
    st.session_state.connected = False
if "messages" not in st.session_state:
    st.session_state.messages = []

st.set_page_config(page_title="Streamlit MCP Host", layout="wide")

# side bar
with st.sidebar:
    st.header("Server Setting")
    
    model_id = st.text_input("Model ID", value="us.amazon.nova-pro-v1:0")
    region_name = st.text_input("AWS Region", value="us-east-1")
    server_url = st.text_input("MCP Server URL", value="")
    system_prompt = st.text_area("System Prompt",
                                 value="""사용자를 잘 도와주는 유능한 에이전트입니다.""")
  
    if st.button("Connect"):
        if not st.session_state.connected:
            with st.spinner("Connecting to server..."):
                try:

                    agent = MCPAgent(model_id=model_id, region_name=region_name, system_prompt=system_prompt)

                    agent.connect_to_server(server_url)

                    st.session_state.agent = agent
                    st.session_state.connected = True
                    
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")
        else:
            st.info("Already connected to server")

    if st.session_state.connected:
        st.success(f"Successfully connected to server: '{server_url}'")

    st.subheader("Available tools")
    if st.session_state.connected:
        for tool in st.session_state.agent.tools:
            with st.expander(f"{tool.tool_name}"):
                st.markdown(f"**description:** {tool.tool_spec['description']}")
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
            
            response_placeholder = st.markdown("", unsafe_allow_html=True)

            try:
                with st.spinner("thinking..."):
                  full_response = response_placeholder.write_stream(st.session_state.agent.stream(prompt))
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                                    
                
            except Exception as e:
                st.error(f"Response failed: {str(e)}")