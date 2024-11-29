import streamlit as st
import boto3
import json
import yaml
from jinja2 import Template
import logging
from botocore.exceptions import ClientError
from typing import List, Dict

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def render_prompt(name: str, description: str, greeting: str, examples: str) -> str:
    with open('./templates/character_template.j2', 'r') as file:
        template = Template(file.read())
    
    with open('./config/character_config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    
    return template.render(
        name=name,
        description=description,
        greeting=greeting,
        examples=examples,
        **config
    )

def chat_with_character(character_info: Dict, user_message: str):
    bedrock_client = boto3.client('bedrock-runtime')
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    
    system_prompts = [{"text": character_info['prompt']}]
    messages = [{"role": "user", "content": [{"text": user_message}]}]
    
    response = bedrock_client.converse_stream(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig={"temperature": 0.7},
        additionalModelRequestFields={"top_k": 200}
    )
    
    full_response = ""
    response_placeholder = st.empty()
    
    for chunk in response['stream']:
        if 'contentBlockDelta' in chunk:
            if 'text' in chunk['contentBlockDelta']['delta']:
                text = chunk['contentBlockDelta']['delta']['text']
                full_response += text
                response_placeholder.markdown(full_response + "▌")
    
    response_placeholder.markdown(full_response)
    return full_response

def main():
    st.title("Character Chatbot Creator")
    
    # Initialize session state
    if 'characters' not in st.session_state:
        st.session_state.characters = {}
    if 'current_character' not in st.session_state:
        st.session_state.current_character = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Sidebar for character creation
    with st.sidebar:
        st.header("Create Character")
        char_name = st.text_input("Character Name")
        char_desc = st.text_area("Character Description")
        char_greeting = st.text_input("Default Greeting")
        
        st.subheader("Example Dialogues")
        example_dialogs = st.text_area(
            "Enter example dialogues",
            height=300,
            placeholder="""<START>
{{user}}: hi
{{char}}: hello"""
        )
        
        if st.button("Create Character"):
            # Generate prompt using template
            prompt = render_prompt(
                name=char_name,
                description=char_desc,
                greeting=char_greeting,
                examples=example_dialogs
            )
            
            st.session_state.characters[char_name] = {
                "name": char_name,
                "description": char_desc,
                "greeting": char_greeting,
                "examples": example_dialogs,
                "prompt": prompt
            }
            st.success(f"Character '{char_name}' created!")
    
    # Character selection and chat interface
    if st.session_state.characters:
        selected_char = st.selectbox(
            "Select Character",
            options=list(st.session_state.characters.keys()),
            key="char_selector"
        )
        
        # Character change handling
        
        if selected_char != st.session_state.current_character:
            st.session_state.current_character = selected_char
            st.session_state.messages = []
            
            # Send greeting
            char_info = st.session_state.characters[selected_char]
            st.session_state.messages.append({"role": "assistant", "content": char_info['greeting']})
    
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Chat input
        if prompt := st.chat_input():
            with st.chat_message("user"):
                st.write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            char_info = st.session_state.characters[st.session_state.current_character]
            with st.chat_message("assistant"):
                response = chat_with_character(char_info, prompt)
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    else:
        st.info("Create a character to start chatting!")

if __name__ == "__main__":
    main()