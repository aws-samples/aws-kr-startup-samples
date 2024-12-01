#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import json
import os

import boto3

from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_aws import ChatBedrock as BedrockChat
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import DocumentDBVectorSearch

from pymongo import MongoClient


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


def _get_llm(model_id='anthropic.claude-instant-v1', region_name='us-east-1'):
  # configure the properties for Claude
  model_kwargs = {
    "max_tokens": 8000,
    "temperature": 0.2,
    "top_k": 250,
    "top_p": 0.9,
    "stop_sequences": ["\\n\\nHuman:"]
  }

  llm = BedrockChat(
    region_name=region_name,
    model_id=model_id,
    model_kwargs=model_kwargs
  )

  return llm


def _get_docdb_collection():
  region = os.environ.get('AWS_REGION', 'us-east-1')

  documentdb_secret_name = os.environ['DOCDB_SECRET_NAME']
  creds = _get_credentials(documentdb_secret_name, region)
  USER, PASSWORD = creds['username'], creds['password']

  DOCDB_HOST = os.environ['DOCDB_HOST']
  DB_NAME = os.environ['DB_NAME']
  COLLECTION_NAME = os.environ['COLLECTION_NAME']

  documentdb_client = MongoClient(
    host=DOCDB_HOST,
    port=27017,
    username=USER,
    password=PASSWORD,
    retryWrites=False,
    tls='true',
    tlsCAFile="global-bundle.pem"
  )

  docdb = documentdb_client[DB_NAME]
  doc_db_collection = docdb[COLLECTION_NAME]

  return doc_db_collection


def build_chain():
  region = os.environ.get('AWS_REGION', 'us-east-1')
  model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-v2:1')

  llm = _get_llm(model_id=model_id, region_name=region)

  embeddings = BedrockEmbeddings(
    region_name=region
  )

  collection = _get_docdb_collection()
  docdb_vectorstore = DocumentDBVectorSearch(
    collection=collection,
    embedding=embeddings
  )

  retriever = docdb_vectorstore.as_retriever(search_kwargs={'similarity': 'cosine', 'k': 4})

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
        print(f"{d.metadata['source']}#{d.metadata['page']}")
    print(bcolors.ENDC)
    print(bcolors.OKCYAN + "Ask a question, start a New search: or CTRL-D to exit." + bcolors.ENDC)
    print(">", end=" ", flush=True)
  print(bcolors.OKBLUE + "Bye" + bcolors.ENDC)
