"""
Helper functions for using Samgemaker Endpoint via langchain
"""
import json
import logging
from typing import List

from langchain_community.embeddings import SagemakerEndpointEmbeddings
from langchain_community.embeddings.sagemaker_endpoint import EmbeddingsContentHandler

logger = logging.getLogger(__name__)


def create_sagemaker_embeddings_from_js_model(embeddings_model_endpoint_name: str, aws_region: str = 'us-east-1') -> SagemakerEndpointEmbeddings:

    # class for serializing/deserializing requests/responses to/from the embeddings model
    class ContentHandler(EmbeddingsContentHandler):
        content_type = "application/json"
        accepts = "application/json"

        def transform_input(self, prompt: str, model_kwargs={}) -> bytes:
            input_str = json.dumps({"text_inputs": prompt, **model_kwargs})
            return input_str.encode('utf-8')

        def transform_output(self, output: bytes) -> str:
            response_json = json.loads(output.read().decode("utf-8"))
            embeddings = response_json["embedding"]
            if len(embeddings) == 1:
                return [embeddings[0]]
            return embeddings

    # all set to create the objects for the ContentHandler and
    # SagemakerEndpointEmbeddings classes
    content_handler = ContentHandler()

    # note the name of the LLM Sagemaker endpoint, this is the model that we would
    # be using for generating the embeddings
    embeddings = SagemakerEndpointEmbeddings(
        endpoint_name=embeddings_model_endpoint_name,
        region_name=aws_region,
        content_handler=content_handler
    )
    return embeddings