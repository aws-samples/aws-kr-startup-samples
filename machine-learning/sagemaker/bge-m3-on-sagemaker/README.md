# Hosting BGE-M3 Embedding Model on Amazon SageMaker

This repository contains example code to deploy the [BGE-M3](https://huggingface.co/BAAI/bge-m3) embedding model on Amazon SageMaker Endpoint.

BGE-M3 is a state-of-the-art embedding model that supports dense, sparse, and ColBERT embeddings, making it highly versatile for various retrieval tasks.

## Features

- Deploy BGE-M3 model to SageMaker endpoint
- Custom inference code for handling different embedding types:
  - Dense embeddings
  - Sparse embeddings
  - ColBERT vectors
- Support for query-specific instructions
- Optimized for GPU inference
- Infrastructure as Code using AWS CDK

## Model Details

| Model | Description | Dimensions | Supported Languages |
|-------|-------------|-----------|---------------------|
| [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | Multi-representation embedding model | 1024 (dense) | 100+ languages |

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
    # Configure AWS credentials
    aws configure
    
    # Configure Virtual Env
    python3 -m venv .venv
    source .venv/bin/activate

    # Install dependencies
    (.venv) pip install -r requirements.txt
    ```

1. Run the following python code to download the model artifacts from Hugging Face model hub.
    ```python
    from huggingface_hub import snapshot_download
    from pathlib import Path

    model_dir = Path('model')
    model_dir.mkdir(exist_ok=True)

    model_id = "LGAI-EXAONE/EXAONE-Deep-7.8B"
    snapshot_download(model_id, local_dir=model_dir)
    ```

   
1. Upload model artifacts into `s3`
    ```sh
    (.venv) export MODEL_URI="s3://{<i>bucket_name</i>}/{<i>key_prefix</i>}/"
    (.venv) aws s3 cp model/ ${MODEL_URI} --recursive
    ```
   
    Then update the `model_data_url` in `cdk_stacks/bge_m3_endpoint_stack.py`:
    ```python
    # Replace `your-bucket` with your actual S3 bucket name
    # model_data_url="s3://your-bucket/BAAI/inference_code/inference_code.tar.gz"
    ```

1. Deploy the stack:
   ```bash
   # Synthesize CloudFormation template
   cdk synth
   
   # Deploy the stack
   cdk deploy
   ```

    The CDK stack will create:
   - IAM role with necessary permissions
   - SageMaker model
   - SageMaker endpoint configuration
   - SageMaker endpoint


    To customize the deployment further, edit the `cdk_stacks/bge_m3_endpoint_stack.py` file.

## Usage

Once deployed, you can use the endpoint to generate embeddings for text:

```python
import boto3
import json

smr_client = boto3.client("sagemaker-runtime")

def get_vector_by_sm_endpoint(questions, smr_client, endpoint_name):
    response_model = smr_client.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps(
            {
                "inputs": questions,
                'return_sparse': True,
                'return_colbert_vecs': True,
            }
        ),
        ContentType="application/json",
    )
    json_str = response_model['Body'].read().decode('utf8')
    json_obj = json.loads(json_str)
    return json_obj

# Example usage
text1 = "How cute your dog is!"
text2 = "Your dog is so cute."
text3 = "The mitochondria is the powerhouse of the cell."

embeddings = get_vector_by_sm_endpoint([text1, text2, text3], smr_client, endpoint_name)
```

### Embedding Types

BGE-M3 supports multiple embedding types that can be requested in the API call:

1. **Dense Embeddings**: Standard vector embeddings (default)
2. **Sparse Embeddings**: Lexical weights for sparse retrieval
3. **ColBERT Vectors**: Token-level embeddings for fine-grained matching

Example of requesting all embedding types:
```python
response = smr_client.invoke_endpoint(
    EndpointName=endpoint_name,
    Body=json.dumps({
        "inputs": ["Your text here"],
        "return_dense": True,
        "return_sparse": True,
        "return_colbert_vecs": True,
        "is_query": True,
        "instruction": "Represent this sentence for searching relevant passages:"
    }),
    ContentType="application/json"
)
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
