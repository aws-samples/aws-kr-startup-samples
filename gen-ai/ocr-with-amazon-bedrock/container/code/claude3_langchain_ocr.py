#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import base64
import os

import boto3
from langchain_aws import ChatBedrock as BedrockChat
from langchain_core.messages import HumanMessage


MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')


def build_chain():
  region_name = boto3.Session().region_name
  model_id = MODEL_ID

  llm = BedrockChat(
    model_id=model_id,
    model_kwargs={
      'max_tokens': 2000,
      'temperature': 0,
      'top_p': 0.999,
      'top_k': 250,
    },
    region_name=region_name
  )

  return llm


def run_chain(chain, base64_image):
  prompt = "Extract all text from the image and separate each line or text segment with a newline character."

  messages = [
    HumanMessage(
      content=[
        {"type": "text", "text": prompt},
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}"
          }
        }
      ]
    )
  ]

  completion = chain.invoke(messages)
  return completion.content


if __name__ == "__main__":
  import sys


  def _encode_image(image_path):
    """Getting the base64 string"""
    with open(image_path, "rb") as image_file:
      return base64.b64encode(image_file.read()).decode("utf-8")

  image_path = sys.argv[1]
  base64_image = _encode_image(image_path)

  chain = build_chain()
  result = run_chain(chain, base64_image)
  print(result)
