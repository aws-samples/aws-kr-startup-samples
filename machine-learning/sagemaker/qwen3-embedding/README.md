# Hosting Qwen3 Embedding (0.6B) Model on Amazon SageMaker

This repository contains example code to deploy the [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) model on Amazon SageMaker Endpoint.

The Qwen3 Embedding model series is the latest proprietary model of the Qwen family, specifically designed for text embedding and ranking tasks.

## Features

- Deploy Qwen3 Embedding model to SageMaker endpoint
- Optimized for GPU inference
- Infrastructure as Code using AWS CDK

## Model Details
| Model Type | Models | Size | Layers | Sequence Length | Embedding Dimension | MRL Support | Instruction Aware |
|------------|--------|------|--------|-----------------|-------------------|-------------|------------------|
| Text Embedding | Qwen3-Embedding-0.6B | 0.6B | 28 | 32K | 1024 | Yes | Yes |
| Text Embedding | Qwen3-Embedding-4B | 4B | 36 | 32K | 2560 | Yes | Yes |
| Text Embedding | Qwen3-Embedding-8B | 8B | 36 | 32K | 4096 | Yes | Yes |
| Text Reranking | Qwen3-Reranker-0.6B | 0.6B | 28 | 32K | - | - | Yes |
| Text Reranking | Qwen3-Reranker-4B | 4B | 36 | 32K | - | - | Yes |
| Text Reranking | Qwen3-Reranker-8B | 8B | 36 | 32K | - | - | Yes |

## Deployment Options

### Option 1: Using Jupyter Notebook

The notebook in `src/notebook/deploy_bge_m3_on_sagemaker_endpoint.ipynb` provides step-by-step instructions for:

1. Downloading the model checkpoint from Hugging Face
2. Uploading the model to Amazon S3
3. Creating custom inference code
4. Deploying the model to a SageMaker endpoint
5. Testing the endpoint with example queries

### Option 2: Using AWS CDK

This project includes AWS CDK code for automated deployment of the SageMaker endpoint:

1. Set up your AWS environment:
    
    ```bash
    # Clone this source code
    git clone --depth=1 https://github.com/aws-samples/aws-kr-startup-samples.git
    cd aws-kr-startup-samples
    git sparse-checkout init --cone
    git sparse-checkout set machine-learning/sagemaker/qwen3-embedding
    cd machine-learning/sagemaker/qwen3-embedding
    
    # Configure AWS credentials
    aws configure

    # Configure Virtual Env
    python3 -m venv .venv
    source .venv/bin/activate

    # Install dependencies
    (.venv) pip install -r requirements.txt
    ```

1. Create a bucket
    ```sh
    # replace
    (.venv) export BUCKET_NAME=your-bucket
    (.venv) aws s3 mb s3://${BUCKET_NAME}
    (.venv) export MODEL_URI="s3://${BUCKET_NAME}/model/Qwen/Qwen3-Embedding-0.6B"
    (.venv) export CODE_URI="s3://${BUCKET_NAME}/inference_code/Qwen/Qwen3-Embedding-0.6B/"

    ```

1. Run the following python code to download the model artifacts from Hugging Face model hub.
    ```python
    from huggingface_hub import snapshot_download
    from pathlib import Path

    model_dir = Path('model')
    model_dir.mkdir(exist_ok=True)

    model_id = "Qwen/Qwen3-Embedding-0.6B"
    snapshot_download(model_id, local_dir=model_dir)
    ```

   
1. Upload model artifacts into `s3`
    ```sh
    (.venv) aws s3 cp model/ ${MODEL_URI} --recursive
    ```
   

1. Upload custom inference code into `s3`

    First update the `option.model_id`in `inference_code/serving.properties`
    ```sh
    # Replace 
    # option.model_id="s3://your-bucket/model/Qwen/Qwen3-Embedding-0.6B"
    ```

    Then the custom inference code into `s3`
    ```sh
    (.venv) tar czvf inference_code.tar.gz inference_code
    (.venv) aws s3 cp inference_code.tar.gz ${CODE_URI}
    ```

    Update the `model_data_url` in `cdk_stacks/bge_m3_endpoint_stack.py`:
    ```sh
    # Replace `your-bucket` with your actual S3 bucket name
    # model_data_url="s3://your-bucket/inference_code/Qwen/Qwen3-Embedding-0.6B/inference_code.tar.gz"
    ```


1. Deploy the stack:
   ```bash
   # Synthesize CloudFormation template
   (.venv) cdk synth
   
   # Deploy the stack
   (.venv) cdk deploy
   ```

    The CDK stack will create:
   - IAM role with necessary permissions
   - SageMaker model
   - SageMaker endpoint configuration
   - SageMaker endpoint


    To customize the deployment further, edit the `cdk_stacks/bge_m3_endpoint_stack.py` file.

## Usage

Once deployed, you can use the endpoint to generate embeddings for text.
You may need to install the numpy library: `pip install numpy`

```python
import boto3
import json
import numpy as np

smr_client = boto3.client("sagemaker-runtime")
# Use the endpoint name from your CDK output
endpoint_name = "qwen3-embedding-0-6b-endpoint" 

def get_embeddings(texts, is_query=False, dim=-1):
    """
    Invokes the SageMaker endpoint to get embeddings.
    - For queries, set is_query=True.
    - For documents, is_query can be False or omitted.
    - To get Matryoshka embeddings, specify the desired dimension with `dim`.
    """
    payload = {
        "inputs": texts,
        "is_query": is_query
    }
    if dim > 0:
        payload["dim"] = dim
    
    response = smr_client.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps(payload),
        ContentType="application/json",
    )
    # The model returns a JSON object with the key "dense_embeddings"
    json_str = response['Body'].read().decode('utf8')
    response_json = json.loads(json_str)
    return response_json

# --- Example Usage (Default Dimension) ---

# 1. Define queries and documents
queries = [
    "What is the capital of China?",
    "Explain gravity",
]
documents = [
    "The capital of China is Beijing.",
    "Gravity is a force that attracts two bodies towards each other. It gives weight to physical objects and is responsible for the movement of planets around the sun.",
]

print("--- Default Dimension Example ---")
print("1. Embedding queries...")
query_response = get_embeddings(queries, is_query=True)
query_embeddings = query_response['dense_embeddings']

print("2. Embedding documents...")
doc_response = get_embeddings(documents)
doc_embeddings = doc_response['dense_embeddings']

# 4. Calculate similarity scores
scores = np.dot(np.array(query_embeddings), np.array(doc_embeddings).T)

print("\n--- Results (Default Dimension) ---")
print("Query embeddings shape:", np.array(query_embeddings).shape)
print("Document embeddings shape:", np.array(doc_embeddings).shape)
print("Similarity scores (dot product):")
print(scores.tolist())

# --- Matryoshka Embedding Example (dim=1024) ---
print("\n--- Matryoshka Embedding Example (dim=1024) ---")
dim = 1024

print(f"1. Embedding queries with dimension {dim}...")
query_response_matryoshka = get_embeddings(queries, is_query=True, dim=dim)
query_embeddings_matryoshka = query_response_matryoshka['dense_embeddings']

print(f"2. Embedding documents with dimension {dim}...")
doc_response_matryoshka = get_embeddings(documents, dim=dim)
doc_embeddings_matryoshka = doc_response_matryoshka['dense_embeddings']

# Calculate similarity scores
scores_matryoshka = np.dot(np.array(query_embeddings_matryoshka), np.array(doc_embeddings_matryoshka).T)

print(f"\n--- Results (dim={dim}) ---")
print("Query embeddings shape:", np.array(query_embeddings_matryoshka).shape)
print("Document embeddings shape:", np.array(doc_embeddings_matryoshka).shape)
print("Similarity scores (dot product):")
print(scores_matryoshka.tolist())

print("\nMost similar document for each query (using default dimension embeddings):")
for i, query in enumerate(queries):
    most_similar_doc_index = np.argmax(scores[i])
    print(f"Query: '{query}'")
    print(f"Most similar document: '{documents[most_similar_doc_index]}'")
    print(f"Score: {scores[i][most_similar_doc_index]:.4f}\n")
```


## Clean Up

If you deployed using CDK, you can remove all resources with:
```bash
cdk destroy
```

## References

- [BGE-M3 Hugging Face Model Card](https://huggingface.co/BAAI/bge-m3)
- [FlagEmbedding GitHub Repository](https://github.com/FlagOpen/FlagEmbedding)
- [Amazon SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/whatis.html)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/latest/guide/home.html)
