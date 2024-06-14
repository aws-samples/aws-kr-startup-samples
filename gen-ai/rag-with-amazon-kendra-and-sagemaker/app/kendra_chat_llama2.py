#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

# Copyright 2016 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0 License
#
# https://github.com/aws-samples/amazon-kendra-langchain-extensions/blob/main/kendra_retriever_samples/kendra_chat_flan_xl.py
#

import sys
import json
import os

from langchain_community.retrievers import AmazonKendraRetriever
from langchain_community.llms import SagemakerEndpoint
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.llms.sagemaker_endpoint import LLMContentHandler


class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKCYAN = '\033[96m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'


MAX_HISTORY_LENGTH = 5


def build_chain():
  region = os.environ["AWS_REGION"]
  kendra_index_id = os.environ["KENDRA_INDEX_ID"]
  text2text_model_endpoint = os.environ["TEXT2TEXT_ENDPOINT_NAME"]

  # https://github.com/aws/amazon-sagemaker-examples/blob/main/introduction_to_amazon_algorithms/jumpstart-foundation-models/llama-2-chat-completion.ipynb
  class ContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs: dict) -> bytes:
      system_prompt = "You are a helpful assistant. Always answer to questions as helpfully as possible." \
                      " If you don't know the answer to a question, say I don't know the answer"

      payload = {
        "inputs": [
          [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
          ],
        ],
        "parameters": model_kwargs,
      }
      input_str = json.dumps(payload)
      return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
      response_json = json.loads(output.read().decode("utf-8"))
      content = response_json[0]["generation"]["content"]
      return content


  content_handler = ContentHandler()

  # https://github.com/aws/amazon-sagemaker-examples/blob/main/introduction_to_amazon_algorithms/jumpstart-foundation-models/llama-2-text-completion.ipynb
  model_kwargs = {
    "max_new_tokens": 500, #256
    "top_p": 0.9,
    "temperature": 0.6,
    "return_full_text": False,
  }

  llm = SagemakerEndpoint(
            endpoint_name=text2text_model_endpoint,
            region_name=region,
            model_kwargs=model_kwargs,
            endpoint_kwargs={"CustomAttributes": "accept_eula=true"},
            content_handler=content_handler)

  retriever = AmazonKendraRetriever(index_id=kendra_index_id, region_name=region, top_k=3)

  prompt_template = """Answer based on context:\n\n{context}\n\n{question}"""

  PROMPT = PromptTemplate(
      template=prompt_template, input_variables=["context", "question"]
  )

  condense_qa_template = """
  Given the following conversation and a follow up question, rephrase the follow up question
  to be a standalone question.

  Chat History:
  {chat_history}
  Follow Up Input: {question}
  Standalone question:"""

  standalone_question_prompt = PromptTemplate.from_template(condense_qa_template)

  qa = ConversationalRetrievalChain.from_llm(
      llm=llm,
      retriever=retriever,
      condense_question_prompt=standalone_question_prompt,
      return_source_documents=True,
      combine_docs_chain_kwargs={"prompt": PROMPT},
      verbose=False
  )

  return qa


def run_chain(chain, prompt: str, history=[]):
   return chain.invoke({"question": prompt, "chat_history": history})


if __name__ == "__main__":
  chat_history = []
  qa = build_chain()
  print(bcolors.OKBLUE + "Hello! How can I help you?" + bcolors.ENDC)
  print(bcolors.OKCYAN + "Ask a question, start a New search: or CTRL-D to exit." + bcolors.ENDC)
  print(">", end=" ", flush=True)
  for query in sys.stdin:
    if (query.strip().lower().startswith("new search:")):
      query = query.strip().lower().replace("new search:","")
      chat_history = []
    elif (len(chat_history) == MAX_HISTORY_LENGTH):
      chat_history.pop(0)
    result = run_chain(qa, query, chat_history)
    chat_history.append((query, result["answer"]))
    print(bcolors.OKGREEN + result['answer'] + bcolors.ENDC)
    if 'source_documents' in result:
      print(bcolors.OKGREEN + 'Sources:')
      for d in result['source_documents']:
        print(d.metadata['source'])
    print(bcolors.ENDC)
    print(bcolors.OKCYAN + "Ask a question, start a New search: or CTRL-D to exit." + bcolors.ENDC)
    print(">", end=" ", flush=True)
  print(bcolors.OKBLUE + "Bye" + bcolors.ENDC)
