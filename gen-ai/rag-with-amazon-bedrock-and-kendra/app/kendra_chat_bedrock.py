# Copyright 2016 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0 License
#
# https://github.com/aws-samples/amazon-kendra-langchain-extensions/blob/main/kendra_retriever_samples/kendra_chat_flan_xl.py
#

import sys
import os

import boto3

from langchain_aws import AmazonKendraRetriever
from langchain_aws import ChatBedrock as BedrockChat
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import (
  create_history_aware_retriever,
  create_retrieval_chain
)
from langchain_core.prompts import (
  ChatPromptTemplate,
  MessagesPlaceholder,
  PromptTemplate
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


def build_chain():
  region = os.environ["AWS_REGION"]
  kendra_index_id = os.environ["KENDRA_INDEX_ID"]
  model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-v2:1')

  bedrockruntime_client = boto3.client('bedrock-runtime',
    region_name=region)

  #XXX: Support for claude v3 models. #18630
  # https://github.com/langchain-ai/langchain/pull/18630
  llm = BedrockChat(
    model_id=model_id,
    client=bedrockruntime_client,
    model_kwargs={
      "max_tokens": 512,
      "temperature": 0,
      "top_p": 0.9
    }
  )

  retriever = AmazonKendraRetriever(index_id=kendra_index_id, region_name=region, min_score_confidence=0.0001)

  condense_qa_template = """Given the following conversation and a follow up question, rephrase the follow up question
to be a standalone question.

Chat History:
{chat_history}
Follow Up Input: {input}
Standalone question:"""
  standalone_question_prompt = PromptTemplate.from_template(condense_qa_template)

  history_aware_retriever = create_history_aware_retriever(
    llm, retriever, standalone_question_prompt
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
