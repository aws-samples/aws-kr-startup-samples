import streamlit as st
import boto3
from langchain_aws import ChatBedrock
from langchain.schema import HumanMessage, AIMessage, SystemMessage

def read_system_message(file_path='prompts.txt'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
        return content
    except FileNotFoundError:
        st.error(f"Error: {file_path} 파일을 찾을 수 없습니다.")
        return "You are a helpful AI assistant for analyzing AWS WAF v2 Logs from AWS Athena."
        
# Bedrock Client Setting
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"  
)

# ChatBedrock Model initialize
chat = ChatBedrock(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    client=bedrock_runtime,
    model_kwargs={
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0.7
    }
)

# Streamlit App Setting
st.title("Text to SQL for Athena")

# 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        SystemMessage(content=read_system_message())
    ]

# 채팅 기록 표시
for message in st.session_state.messages[1:]:  # SystemMessage 제외
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(message.content)

# 사용자 입력 처리
if prompt := st.chat_input("AWS WAFv2 Log 로 부터 알고 싶은 내용을 질문하세요"):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # AI 응답 생성
    response = chat.invoke(st.session_state.messages)
    st.session_state.messages.append(AIMessage(content=response.content))
    with st.chat_message("assistant"):
        st.markdown(response.content)