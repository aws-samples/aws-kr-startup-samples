#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import json
import os

import boto3

from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate

from langchain_community.llms import SagemakerEndpoint
from langchain_community.llms.sagemaker_endpoint import LLMContentHandler

from langchain_community.embeddings import BedrockEmbeddings

from langchain_aws.vectorstores.inmemorydb import InMemoryVectorStore

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

class ContentHandler(LLMContentHandler):
  content_type = "application/json"
  accepts = "application/json"

  def transform_input(self, prompt: str, model_kwargs: dict) -> bytes:
    system_prompt = "You are a helpful assistant. Always answer to questions as helpfully as possible." \
                    " If you don't know the answer to a question, say I don't know the answer"

    payload = {
      "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
      ],
      **model_kwargs,
    }
    input_str = json.dumps(payload)
    return input_str.encode("utf-8")

  def transform_output(self, output: bytes) -> str:
    response_json = json.loads(output.read().decode("utf-8"))
    content = response_json["choices"][0]["message"]["content"]
    return content


def _get_credentials(secret_id: str, region_name: str='us-east-1') -> str:
  client = boto3.client('secretsmanager', region_name=region_name)
  response = client.get_secret_value(SecretId=secret_id)
  secrets_value = json.loads(response['SecretString'])
  return secrets_value


def _get_llm(endpoint_name: str, region_name: str='us-east-1'):
  # configure the properties for Llama3
  model_kwargs = {
    "top_p": 0.6,
    "temperature": 0.9,
    "max_tokens": 512,
    "stop": ["<|eot_id|>"]
  }

  llm = SagemakerEndpoint(
    endpoint_name=endpoint_name,
    region_name=region_name,
    model_kwargs=model_kwargs,
    endpoint_kwargs={"CustomAttributes": "accept_eula=true"},
    content_handler=ContentHandler()
  )

  return llm


def build_chain():
  region = os.environ.get('AWS_REGION', 'us-east-1')

  memorydb_secret_name = os.environ['MEMORYDB_SECRET_NAME']
  creds = _get_credentials(memorydb_secret_name, region)
  USER, PASSWORD = creds['username'], creds['password']

  REDIS_HOST = os.environ['REDIS_HOST']
  REDIS_URL = f"rediss://{USER}:{PASSWORD}@{REDIS_HOST}:6379/ssl=True&ssl_cert_reqs=none"
  INDEX_NAME = os.environ['INDEX_NAME']

  text2text_model_endpoint = os.environ["TEXT2TEXT_ENDPOINT_NAME"]
  llm = _get_llm(endpoint_name=text2text_model_endpoint, region_name=region)

  embeddings = BedrockEmbeddings(
    region_name=region
  )

  memorydb_client = InMemoryVectorStore(
    redis_url=REDIS_URL,
    index_name=INDEX_NAME,
    embedding=embeddings
  )

  retriever = memorydb_client.as_retriever()

  prompt_template = """
  The following is a friendly conversation between a human and an AI.
  The AI is talkative and provides lots of specific details from its context.
  If the AI does not know the answer to a question, it truthfully says it
  does not know.
  {context}
  Instruction: Based on the above documents, provide a detailed answer for, {question} Answer "don't know"
  if not present in the document.
  Solution:"""

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
    combine_docs_chain_kwargs={"prompt": PROMPT}
  )

  return qa


def run_chain(chain, prompt: str, history=[]):
  PREAMBLE = "<|start_header_id|>assistant<|end_header_id|>"

  result = chain.invoke({"question": prompt, "chat_history": history})
  answer = result["answer"]
  if answer.startswith(PREAMBLE):
    result["answer"] = answer[len(PREAMBLE):]
  return result


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
        print(d.metadata['id'])
    print(bcolors.ENDC)
    print(bcolors.OKCYAN + "Ask a question, start a New search: or CTRL-D to exit." + bcolors.ENDC)
    print(">", end=" ", flush=True)
  print(bcolors.OKBLUE + "Bye" + bcolors.ENDC)
