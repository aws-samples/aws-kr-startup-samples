import asyncio
import json
import logging
import os
import random
from typing import List, Dict, Any

import boto3
import streamlit as st
from botocore.exceptions import ClientError

# Constants
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")

MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
MAX_TOKENS = 1000
TEMPERATURE = 0.1
TOP_P = 0.9

KIM_CHEOMJI_BASIC_INFO = """
김첨지는 1920년대 일제강점기 서울의 가난한 인력거꾼입니다. 그는 병든 아내와 어린 자식을 부양하기 위해 열심히 일합니다. 
거친 말투를 사용하지만 가족에 대한 깊은 사랑과 책임감을 가지고 있습니다. 불운한 상황에 자주 처하며, 때로는 분노와 좌절을 표현합니다. 
그의 말투는 서울 방언을 사용하며, "이 난장맞을", "오라질 년", "젠장맞을", "빌어먹을" 등의 거칠고 직설적인 표현을 자주 사용합니다.
"""

CHARACTERISTIC_EXPRESSIONS = ["난장맞을", "오라질", "젠장맞을", "빌어먹을"]

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
bedrock_runtime = boto3.client('bedrock-runtime')

async def retrieve_information(query: str) -> List[Dict[str, Any]]:
    """Asynchronously retrieve information from the knowledge base."""
    try:
        logger.debug(f"Retrieving information for query: {query}")
        response = await asyncio.to_thread(
            bedrock_agent_runtime.retrieve,
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 12,
                    'overrideSearchType': 'HYBRID',
                    'filter': {
                        'equals': {
                            'key': 'title',
                            'value': 'luckyday'
                        }
                    }
                }
            },
            retrievalQuery={'text': query}
        )
        logger.debug(f"Retrieved information: {response['retrievalResults']}")
        return response['retrievalResults']
    except ClientError as e:
        logger.error(f"Error retrieving information: {e}")
        return []

def process_retrieve_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process and extract relevant information from retrieval results."""
    processed_results = [
        {
            'text': result['content']['text'],
            'character': result['metadata'].get('character', ''),
            'setting': result['metadata'].get('setting', ''),
            'keyThemes': result['metadata'].get('keyThemes', [])
        }
        for result in results
    ]
    logger.debug(f"Processed retrieve results: {processed_results}")
    return processed_results

def generate_system_message(processed_info: List[Dict[str, Any]]) -> str:
    """Generate a system message for the LLM based on the processed information."""
    context = "\n".join(f"정보 {i+1}: {info['text']}" for i, info in enumerate(processed_info))
    
    system_message = f"""당신은 김첨지의 역할을 맡고 있습니다. 다음 정보를 바탕으로 질문에 답변해주세요:

김첨지 기본 정보:
{KIM_CHEOMJI_BASIC_INFO}

검색된 관련 정보:
{context}

김첨지의 성격과 상황에 맞게 답변해주세요. 검색된 정보를 최대한 활용하여 구체적이고 상황에 맞는 응답을 생성하되, 김첨지의 특징적인 말투와 표현을 반드시 사용하세요. 답변은 30자 내로 짧게 하세요."""

    logger.debug(f"Generated system message: {system_message}")
    return system_message

def generate_message(bedrock_runtime, model_id, system_prompt, messages, max_tokens):
    """Generate a message using the Bedrock Claude 3 API."""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "system": system_prompt,
        "messages": messages
    })

    logger.debug(f"API request body: {body}")

    try:
        response = bedrock_runtime.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        logger.debug(f"API response: {response_body}")
        return response_body['content'][0]['text']
    except ClientError as e:
        logger.error(f"Error generating message: {e}")
        return "죄송합니다. 지금은 대답하기 어렵습니다. 나중에 다시 물어봐주세요."

def post_process_response(response: str) -> str:
    """Ensure the response includes characteristic expressions."""
    if not any(expr in response for expr in CHARACTERISTIC_EXPRESSIONS):
        expression = random.choice(CHARACTERISTIC_EXPRESSIONS)
        response = f"{expression} {response}"
    logger.debug(f"Post-processed response: {response}")
    return response

def prepare_conversation_history(messages):
    if not messages:
        return []
    
    # Ensure the conversation starts with a user message
    if messages[0]["role"] != "user":
        messages = messages[1:]
    
    # Ensure alternating user and assistant messages
    prepared_history = []
    for i in range(0, len(messages) - 1, 2):
        if i + 1 < len(messages):
            prepared_history.extend([messages[i], messages[i+1]])
    
    # If the last message is from the user, include it
    if len(messages) % 2 != 0:
        prepared_history.append(messages[-1])
    
    return prepared_history[-8:]  # Limit to last 4 exchanges (8 messages)

async def generate_kim_cheomji_response(query: str, conversation_history: List[Dict[str, str]]) -> str:
    """Main function to generate Kim Cheomji's response."""
    logger.info(f"Generating response for query: {query}")
    logger.debug(f"Conversation history: {conversation_history}")

    results = await retrieve_information(query)
    processed_info = process_retrieve_results(results)
    system_message = generate_system_message(processed_info)
    
    messages = conversation_history
    
    logger.debug(f"Messages sent to API: {messages}")
    
    response = generate_message(bedrock_runtime, MODEL_ID, system_message, messages, MAX_TOKENS)
    final_response = post_process_response(response)
    
    logger.info(f"Generated response: {final_response}")
    return final_response

def main():
    st.title("김첨지와의 대화")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("김첨지에게 무엇을 물어보시겠습니까?"):
        logger.info(f"User input: {prompt}")
        
        conversation_history = prepare_conversation_history(st.session_state.messages)
        conversation_history.append({"role": "user", "content": prompt})
                
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            logger.debug(f"Conversation history sent to generate_kim_cheomji_response: {conversation_history}")
            final_response = asyncio.run(generate_kim_cheomji_response(prompt, conversation_history))
            st.markdown(final_response)
            
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({"role": "assistant", "content": final_response})

if __name__ == "__main__":
    main()