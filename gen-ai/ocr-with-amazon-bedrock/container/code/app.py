#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import base64
import boto3
import json
import os

import streamlit as st
from PIL import Image


MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

def extract_text_from_image(bedrock_runtime_client, content_image):
  message_mm = [
    {
      "role": "user",
      "content": [
        {
          "type": "image",
           "source": {
             "type": "base64",
             "media_type": "image/jpeg",
             "data": content_image
           }
        },
        {
          "type": "text",
          "text": "Extract all text from the image and separate each line or text segment with a newline character."
        }
      ]
    }
  ]

  model_kwargs = {
    'max_tokens': 2000,
    'temperature': 0,
    'top_p': 0.999,
    'top_k': 250,
  }

  body = json.dumps({
      "anthropic_version": "bedrock-2023-05-31",
      "messages": message_mm,
      **model_kwargs
    }
  )

  model_id = MODEL_ID
  response = bedrock_runtime_client.invoke_model(body=body,
                           modelId=model_id)
  response_body = json.loads(response.get('body').read())
  if response_body['stop_reason'] == 'end_turn':
    text = response_body['content'][0]['text']
    #XXX: For more information, see https://github.com/streamlit/streamlit/issues/868
    return '  \n'.join(text.split('\n'))
  else:
    return f"ERROR: {response_body['stop_reason']}"


def main():
  region_name = boto3.Session().region_name
  bedrock_runtime_client = boto3.client('bedrock-runtime', region_name=region_name)

  st.set_page_config(layout="wide", page_title="Image Understanding")
  st.title("Image Understanding")
  st.write("Upload an image and see any text found in the image!")

  uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

  if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption=f"Uploaded Image: {uploaded_file.name}")

    bytes_data = uploaded_file.getvalue()
    base64_string = base64.b64encode(bytes_data).decode("utf-8")

    st.subheader("Output")
    text = extract_text_from_image(bedrock_runtime_client, base64_string)
    st.write(text)


if __name__ == "__main__":
  main()
