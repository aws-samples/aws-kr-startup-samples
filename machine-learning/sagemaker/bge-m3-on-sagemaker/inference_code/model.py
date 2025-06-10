from djl_python import Input, Output
import torch
import logging
import os
from FlagEmbedding import BGEM3FlagModel

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"--device={device}")


def load_model(properties):
    tensor_parallel = properties.get("tensor_parallel_degree", 1)  # Default value 1
    model_location = properties.get("model_dir", "/opt/ml/model")

    if "model_id" in properties:
        model_location = properties["model_id"]

    logging.info(f"Loading model from {model_location}")

    model = BGEM3FlagModel(model_location, use_fp16=True)
    return model


model = None


def handle(inputs: Input):
    global model
    if model is None:
        model = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None

    data = inputs.get_as_json()

    # Extract parameters from JSON
    input_sentences = data.get("inputs", [])
    if isinstance(input_sentences, str):
        input_sentences = [input_sentences]  # Convert single input to list

    is_query = data.get("is_query", False)
    max_length = data.get("max_length", 2048)
    instruction = data.get("instruction", "")

    # Extract optional parameters
    return_dense = data.get("return_dense", True)  # Default: True
    return_sparse = data.get("return_sparse", False)  # Default: False
    return_colbert_vecs = data.get("return_colbert_vecs", False)  # Default: False

    logging.info(f"inputs: {input_sentences}")
    logging.info(f"is_query: {is_query}")
    logging.info(f"instruction: {instruction}")
    logging.info(
        f"return_dense: {return_dense}, return_sparse: {return_sparse}, return_colbert_vecs: {return_colbert_vecs}"
    )

    # Add instruction for queries if provided
    if is_query and instruction:
        input_sentences = [instruction + sent for sent in input_sentences]

    # Generate embeddings with specified options
    sentence_embeddings = model.encode(
        input_sentences,
        max_length=max_length,
        return_dense=return_dense,
        return_sparse=return_sparse,
        return_colbert_vecs=return_colbert_vecs,
    )

    # Format output JSON
    result = {}
    if return_dense:
        result["dense_embeddings"] = sentence_embeddings.get("dense_vecs", [])
    if return_sparse:
        result["sparse_embeddings"] = sentence_embeddings.get("lexical_weights", [])
    if return_colbert_vecs:
        result["colbert_vectors"] = sentence_embeddings.get("colbert_vecs", [])

    return Output().add_as_json(result)
