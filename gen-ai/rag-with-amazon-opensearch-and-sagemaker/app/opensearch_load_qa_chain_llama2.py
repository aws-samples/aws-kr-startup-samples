#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4 expandtab

import os
import json
import logging
import sys
from typing import List, Callable
from urllib.parse import urlparse

import boto3

from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_community.embeddings import SagemakerEndpointEmbeddings
from langchain_community.embeddings.sagemaker_endpoint import EmbeddingsContentHandler

from langchain_community.llms import SagemakerEndpoint
from langchain_community.llms.sagemaker_endpoint import LLMContentHandler

from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain


logger = logging.getLogger()
logging.basicConfig(format='%(asctime)s,%(module)s,%(processName)s,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stderr)

class SagemakerEndpointEmbeddingsJumpStart(SagemakerEndpointEmbeddings):
    def embed_documents(
        self, texts: List[str], chunk_size: int = 5
    ) -> List[List[float]]:
        """Compute doc embeddings using a SageMaker Inference Endpoint.

        Args:
            texts: The list of texts to embed.
            chunk_size: The chunk size defines how many input texts will
                be grouped together as request. If None, will use the
                chunk size specified by the class.

        Returns:
            List of embeddings, one for each text.
        """
        results = []
        _chunk_size = len(texts) if chunk_size > len(texts) else chunk_size
        for i in range(0, len(texts), _chunk_size):
            response = self._embedding_func(texts[i : i + _chunk_size])
            #print(response)
            results.extend(response)
        return results


class ContentHandlerForEmbeddings(EmbeddingsContentHandler):
    """
    encode input string as utf-8 bytes, read the embeddings
    from the output
    """
    content_type = "application/json"
    accepts = "application/json"
    def transform_input(self, prompt: str, model_kwargs = {}) -> bytes:
        input_str = json.dumps({"text_inputs": prompt, **model_kwargs})
        return input_str.encode('utf-8')

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["embedding"]
        if len(embeddings) == 1:
            return [embeddings[0]]
        return embeddings


class ContentHandlerForTextGeneration(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    # https://github.com/aws/amazon-sagemaker-examples/blob/main/introduction_to_amazon_algorithms/jumpstart-foundation-models/llama-2-chat-completion.ipynb
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


def _create_sagemaker_embeddings(endpoint_name: str, region: str = "us-east-1") -> SagemakerEndpointEmbeddingsJumpStart:
    # create a content handler object which knows how to serialize
    # and deserialize communication with the model endpoint
    content_handler = ContentHandlerForEmbeddings()

    # read to create the Sagemaker embeddings, we are providing
    # the Sagemaker endpoint that will be used for generating the
    # embeddings to the class
    embeddings = SagemakerEndpointEmbeddingsJumpStart(
        endpoint_name=endpoint_name,
        region_name=region,
        content_handler=content_handler
    )
    logger.info(f"embeddings type={type(embeddings)}")

    return embeddings


def _get_credentials(secret_id: str, region_name: str) -> str:

    client = boto3.client('secretsmanager', region_name=region_name)
    response = client.get_secret_value(SecretId=secret_id)
    secrets_value = json.loads(response['SecretString'])
    return secrets_value


def load_vector_db_opensearch(secret_id: str,
                              region: str,
                              opensearch_domain_endpoint: str,
                              opensearch_index: str,
                              embeddings_model_endpoint: str) -> OpenSearchVectorSearch:
    logger.info(f"load_vector_db_opensearch, secret_id={secret_id}, region={region}, "
                f"opensearch_domain_endpoint={opensearch_domain_endpoint}, opensearch_index={opensearch_index}, "
                f"embeddings_model_endpoint={embeddings_model_endpoint}")

    opensearch_url = f"https://{opensearch_domain_endpoint}" if not opensearch_domain_endpoint.startswith('https://') else opensearch_domain_endpoint
    logger.info(f"embeddings_model_endpoint={embeddings_model_endpoint}, opensearch_url={opensearch_url}")

    creds = _get_credentials(secret_id, region)
    http_auth = (creds['username'], creds['password'])
    vector_db = OpenSearchVectorSearch(index_name=opensearch_index,
        embedding_function=_create_sagemaker_embeddings(embeddings_model_endpoint, region),
        opensearch_url=opensearch_url,
        http_auth=http_auth)

    logger.info(f"returning handle to OpenSearchVectorSearch, vector_db={vector_db}")
    return vector_db


def setup_sagemaker_endpoint_for_text_generation(endpoint_name, region: str = "us-east-1") -> Callable:
    parameters = {
        "max_new_tokens": 256,
        "top_p": 0.9,
        "temperature": 0.6,
        "return_full_text": False,
    }

    content_handler = ContentHandlerForTextGeneration()
    sm_llm = SagemakerEndpoint(
        endpoint_name=endpoint_name,
        region_name=region,
        model_kwargs=parameters,
        endpoint_kwargs={"CustomAttributes": "accept_eula=true"},
        content_handler=content_handler)
    return sm_llm


def main():
    region = os.environ["AWS_REGION"]
    opensearch_secret = os.environ["OPENSEARCH_SECRET"]
    opensearch_domain_endpoint = os.environ["OPENSEARCH_DOMAIN_ENDPOINT"]
    opensearch_index = os.environ["OPENSEARCH_INDEX"]
    embeddings_model_endpoint = os.environ["EMBEDDING_ENDPOINT_NAME"]
    text2text_model_endpoint = os.environ["TEXT2TEXT_ENDPOINT_NAME"]

    # initialize vector db and Sagemaker Endpoint
    os_creds_secretid_in_secrets_manager = opensearch_secret
    _vector_db = load_vector_db_opensearch(os_creds_secretid_in_secrets_manager,
        region,
        opensearch_domain_endpoint,
        opensearch_index,
        embeddings_model_endpoint)

    _sm_llm = setup_sagemaker_endpoint_for_text_generation(text2text_model_endpoint, region)

    # Use the vector db to find similar documents to the query
    # the vector db call would automatically convert the query text
    # into embeddings
    query = 'What is SageMaker model monitor? Write your answer in a nicely formatted way.'
    max_matching_docs = 3
    docs = _vector_db.similarity_search(query, k=max_matching_docs)
    logger.info(f"here are the {max_matching_docs} closest matching docs to the query=\"{query}\"")
    for d in docs:
        logger.info(f"---------")
        logger.info(d)
        logger.info(f"---------")

    # now that we have the matching docs, lets pack them as a context
    # into the prompt and ask the LLM to generate a response
    prompt_template = """Answer based on context:\n\n{context}\n\n{question}"""

    prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    logger.info(f"prompt sent to llm = \"{prompt}\"")

    chain = load_qa_chain(llm=_sm_llm, prompt=prompt, verbose=True)
    logger.info(f"\ntype('chain'): \"{type(chain)}\"\n")

    answer = chain.invoke({"input_documents": docs, "question": query}, return_only_outputs=True)['output_text']

    logger.info(f"answer received from llm,\nquestion: \"{query}\"\nanswer: \"{answer}\"")

    resp = {'question': query, 'answer': answer}
    resp['docs'] = docs
    print(resp)


if __name__ == "__main__":
    main()

