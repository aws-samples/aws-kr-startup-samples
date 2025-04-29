import streamlit as st
import asyncio
from src.client import MCPClient
import nest_asyncio


nest_asyncio.apply()

if "loop" not in st.session_state:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    st.session_state.loop = loop

if "messages" not in st.session_state:
    st.session_state.messages = []

if "client" not in st.session_state:
    st.session_state.client = None
    st.session_state.connected = False
    st.session_state.tools = None

st.set_page_config(page_title="Streamlit MCP Host", layout="wide")

# side bar
with st.sidebar:
    st.header("서버 설정")
    
    model_id = st.text_input("모델 ID", value="us.amazon.nova-lite-v1:0")
    region_name = st.text_input("AWS 리전", value="us-east-1")
    server_path = st.text_input("서버 스크립트 경로", value="src/server.py")

    if st.button("서버 연결"):
        if not st.session_state.connected:
            with st.spinner("서버에 연결 중..."):
                try:

                    client = MCPClient(model_id=model_id, region_name=region_name)
                    tools = st.session_state.loop.run_until_complete(client.connect_to_server(server_path))
                    
                    # 세션 상태에 저장
                    st.session_state.client = client
                    st.session_state.connected = True
                    st.session_state.tools = tools
                    st.success(f"서버 '{server_path}'에 연결되었습니다!")
                    
                except Exception as e:
                    st.error(f"서버 연결 실패: {str(e)}")
        else:
            st.info("이미 서버에 연결되어 있습니다.")

    st.subheader("사용 가능한 도구")
    if st.session_state.connected:
        for tool in st.session_state.tools:
            with st.expander(f"{tool.name}"):
                st.markdown(f"**설명:** {tool.description}")
                
                st.markdown("**매개변수:**")
                params = tool.args_schema.get('properties', {})
                required = tool.args_schema.get('required', [])
                
                # 매개변수 테이블 생성
                if params:
                    param_data = []
                    for param_name, param_info in params.items():
                        param_type = param_info.get('type', '')
                        is_required = "✓" if param_name in required else ""
                        param_data.append([param_name, param_type, is_required])
                    
                    st.table({
                        "파라미터": [p[0] for p in param_data],
                        "타입": [p[1] for p in param_data],
                        "필수": [p[2] for p in param_data]
                        })
    else:
        st.warning("서버에 연결해주세요.")

# chat
st.title("Streamlit MCP Host")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("메시지를 입력하세요..."):
    if not st.session_state.connected:
        st.error("서버에 연결되어 있지 않습니다. 먼저 서버에 연결해주세요.")
    else:
        with st.chat_message("user"):
            st.write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):

            response_placeholder = st.empty()
            try:
                response = st.session_state.loop.run_until_complete(st.session_state.client.invoke_agent(prompt, thread_id=42))
                
                # 응답을 보기 좋게 포맷팅
                with st.expander('tool messages'):
                    messages = "\n".join([ str(msg.content) for msg in response["messages"][1:-1]])
                    st.markdown(messages)

                final_message = response["messages"][-1].content
                response_placeholder.markdown(final_message)
                                    
                st.session_state.messages.append({"role": "assistant", "content": final_message})
                
            except Exception as e:
                st.error(f"응답 생성 실패: {str(e)}")
