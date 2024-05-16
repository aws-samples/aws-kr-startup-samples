#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import json
import os

import boto3

from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_community.embeddings import BedrockEmbeddings
from langchain_aws import ChatBedrock as BedrockChat
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import (
  create_history_aware_retriever,
  create_retrieval_chain
)
from langchain_core.prompts import (
  ChatPromptTemplate,
  MessagesPlaceholder
)
from langchain_core.messages import (
    HumanMessage,
    AIMessage
)


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

def _get_credentials(secret_id: str, region_name: str) -> str:
  client = boto3.client('secretsmanager', region_name=region_name)
  response = client.get_secret_value(SecretId=secret_id)
  secrets_value = json.loads(response['SecretString'])
  return secrets_value


def build_chain():
  region = os.environ.get('AWS_REGION', 'us-east-1')
  opensearch_secret = os.environ["OPENSEARCH_SECRET"]
  opensearch_domain_endpoint = os.environ["OPENSEARCH_DOMAIN_ENDPOINT"]
  opensearch_index = os.environ["OPENSEARCH_INDEX"]

  opensearch_url = f"https://{opensearch_domain_endpoint}" if not opensearch_domain_endpoint.startswith('https://') else opensearch_domain_endpoint

  creds = _get_credentials(opensearch_secret, region)
  http_auth = (creds['username'], creds['password'])

  embeddings = BedrockEmbeddings(
    model_id='amazon.titan-embed-text-v1',
    region_name=region
  )

  opensearch_vector_search = OpenSearchVectorSearch(
    opensearch_url=opensearch_url,
    index_name=opensearch_index,
    embedding_function=embeddings,
    http_auth=http_auth
  )

  retriever = opensearch_vector_search.as_retriever(search_kwargs={"k": 3})

  model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-v2:1')
  llm = BedrockChat(
    model_id=model_id,
    region_name=region,
    model_kwargs={
      "max_tokens": 512,
      "temperature": 0,
      "top_p": 0.9
    }
  )

  contextualize_q_system_prompt = """Given a chat history and the latest user question \
which might reference context in the chat history, formulate a standalone question \
which can be understood without the chat history. Do NOT answer the question, \
just reformulate it if needed and otherwise return it as is."""

  contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
  )

  history_aware_retriever = create_history_aware_retriever(
    llm, retriever, contextualize_q_prompt
  )

  qa_system_prompt = """
  The following is a friendly conversation between a human and an AI.
  The AI is talkative and provides lots of specific details from its context.
  If the AI does not know the answer to a question, it truthfully says it
  does not know.
  {context}
  Instruction: Based on the above documents, provide a detailed answer for, {input} Answer "don't know"
  if not present in the document.
  Solution:"""

  qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
  )

  question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

  rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
  return rag_chain


def run_chain(chain, prompt: str, history=[]):
  return chain.invoke({"input": prompt, "chat_history": history})


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
    #XXX: Be sure to preserve message formats when using the Anthropic Claude Messages API.
    # Otherwise, you will enconter the following error,
    #   ValueError: Error raised by bedrock service: An error occurred (ValidationException) when calling the InvokeModel operation:
    #   messages: roles must alternate between "user" and "assistant", but found multiple "user" roles in a row
    # For more information, see https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html
    chat_history.extend([HumanMessage(content=query), AIMessage(content=result["answer"])])
    print(bcolors.OKGREEN + result['answer'] + bcolors.ENDC)
    if 'context' in result:
      print(bcolors.OKGREEN + '\nSources:')
      for d in result['context']:
        print(d.metadata['source'])
    print(bcolors.ENDC)
    print(bcolors.OKCYAN + "Ask a question, start a New search: or CTRL-D to exit." + bcolors.ENDC)
    print(">", end=" ", flush=True)
  print(bcolors.OKBLUE + "Bye" + bcolors.ENDC)
