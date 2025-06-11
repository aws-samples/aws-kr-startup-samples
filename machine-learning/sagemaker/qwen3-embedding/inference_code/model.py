from djl_python import Input, Output
import logging
from vllm import LLM, PoolingParams


def get_detailed_instruct(task_description: str, query: str) -> str:
    """Formats the query with a task-specific instruction."""
    if not task_description:
        task_description = (
            "Given a web search query, retrieve relevant passages that answer the query"
        )
    return f"Instruct: {task_description}\nQuery:{query}"


def load_model(properties):
    model_location = properties.get("model_dir", "/opt/ml/model")

    if "model_id" in properties:
        model_location = properties["model_id"]

    logging.info(f"Loading model from {model_location}")

    # Following the new example:
    # - task="embed" to use the embedding endpoint.
    # - hf_overrides for matryoshka embeddings.
    model = LLM(
        model=model_location,
        task="embed",
        hf_overrides={"is_matryoshka": True},
    )
    return model


model = None


def handle(inputs: Input):
    global model
    if model is None:
        model = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None

    data = inputs.get_as_json()

    input_sentences = data.get("inputs", [])
    if isinstance(input_sentences, str):
        input_sentences = [input_sentences]

    # Parameters from the user's request, based on the new example
    is_query = data.get("is_query", False)
    instruction = data.get(
        "instruction"
    )  # Can be None, get_detailed_instruct will use a default.
    dim = data.get("dim", -1)  # For matryoshka embeddings

    logging.info(f"inputs: {len(input_sentences)} sentences")
    logging.info(f"is_query: {is_query}")
    if instruction:
        logging.info(f"custom instruction: {instruction}")
    logging.info(f"embedding dimension: {dim if dim > 0 else 'default'}")

    if is_query:
        # For queries, add instructions.
        input_texts = [get_detailed_instruct(instruction, q) for q in input_sentences]
    else:
        # For documents, no instruction is needed.
        input_texts = input_sentences

    pooling_params = None
    if dim > 0:
        logging.info(f"Using matryoshka embeddings with dimension: {dim}")
        pooling_params = PoolingParams(dimensions=dim)

    # Get embeddings using model.embed
    logging.info("Calling model.embed on vLLM...")
    outputs = model.embed(input_texts, pooling_params=pooling_params)
    logging.info("model.embed call finished.")

    # Extract embeddings from vLLM output
    embeddings = [o.outputs.embedding for o in outputs]
    logging.info(f"Extracted {len(embeddings)} embeddings.")

    # Format output
    result = {"dense_embeddings": embeddings}
    logging.info("Formatted result into a dictionary.")

    output_obj = Output().add_as_json(result)
    logging.info("Created DJL Output object. Returning from handle function.")

    return output_obj
