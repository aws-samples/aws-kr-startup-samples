import boto3
import os
import json
import time
import argparse
from botocore.exceptions import ClientError
from utils import Colors, print_step, print_success, print_info, exit_on_error

# Parse command line arguments
parser = argparse.ArgumentParser(description='Deploy S3 Vector RAG resources')
parser.add_argument('--region', default='us-west-2', choices=['us-east-1', 'us-east-2', 'us-west-2', 'eu-central-1', 'ap-southeast-2'], help='AWS region (default: us-west-2)')
parser.add_argument('--embedding-model', default='cohere.embed-multilingual-v3', help='Embedding model (default: cohere.embed-multilingual-v3)')
parser.add_argument('--generation-model', default='anthropic.claude-3-5-sonnet-20241022-v2:0', help='Generation model (default: anthropic.claude-3-5-sonnet-20241022-v2:0)')
parser.add_argument('--auto-approval', action='store_true', help='Skip confirmation prompt and proceed automatically')
args = parser.parse_args()

region = args.region
embedding_model = args.embedding_model
generation_model = args.generation_model
auto_approval = args.auto_approval

# Account settings
print(f"{Colors.BOLD}Starting AWS Resource Deployment{Colors.END}")
print("=" * 50)

try:
    session = boto3.session.Session(region_name=region)
    account_id = session.client("sts").get_caller_identity()["Account"]
    print_info(f"Account ID: {account_id}")
    print_info(f"Region: {region}")
    print_info(f"Embedding Model: {embedding_model}")
    print_info(f"Generation Model: {generation_model}")
except Exception as e:
    exit_on_error(f"Failed to get AWS credentials: {str(e)}")

bucket_name = f's3-vectors-{account_id}-{region}-faqs'
vector_bucket_name = f's3-vectors-{account_id}-{region}-embeddings'
index_name = "s3-vectors-index"
kb_role_name='s3-vectors-kb-execution-role'
kb_name='s3-vectors-knowledge-base'

# Show resources to be created
print("\nResources to be created:")
print_info(f"S3 Bucket: {bucket_name}")
print_info(f"Vector Bucket: {vector_bucket_name}")
print_info(f"Vector Index: {index_name}")
print_info(f"IAM Role: {kb_role_name}")
print_info(f"Knowledge Base: {kb_name}")

# Ask for confirmation
if not auto_approval:
    confirm = input(f"\nDo you want to proceed with deployment? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Deployment cancelled.")
        exit(0)
else:
    print("\nAuto-approval enabled. Proceeding with deployment...")

# Knowledge Bases settings
dimension = 1024

# Step 1: Create S3 bucket
print_step(1, 8, "Creating S3 bucket for files")
try:
    s3 = session.client('s3')
    s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": region})
    print_success(f"S3 bucket created: {bucket_name}")
except ClientError as e:
    if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
        print_success(f"S3 bucket already exists: {bucket_name}")
    else:
        exit_on_error(f"Failed to create S3 bucket: {str(e)}")
except Exception as e:
    exit_on_error(f"Failed to create S3 bucket: {str(e)}")

# Step 2: Upload files to S3
print_step(2, 8, "Uploading files to S3 bucket")
try:
    if not os.path.exists('faq'):
        exit_on_error("FAQ directory not found")
    
    files = os.listdir('faq')
    if not files:
        print_info("No files found in FAQ directory")
    else:
        for file in files:
            s3.upload_file(f'faq/{file}', bucket_name, file)
            print_success(f"Uploaded: {file}")
        print_success(f"All {len(files)} files uploaded successfully")
except Exception as e:
    exit_on_error(f"Failed to upload files: {str(e)}")


# Step 3: Create S3 Vector Storage
print_step(3, 8, "Creating S3 Vector Storage")
try:
    s3vectors = session.client('s3vectors')
    s3vectors.create_vector_bucket(vectorBucketName=vector_bucket_name)
    print_success(f"Vector bucket created: {vector_bucket_name}")
except ClientError as e:
    if 'already exists' in str(e).lower():
        print_success(f"Vector bucket already exists: {vector_bucket_name}")
    else:
        exit_on_error(f"Failed to create vector bucket: {str(e)}")
except Exception as e:
    exit_on_error(f"Failed to create vector bucket: {str(e)}")

# Step 4: Create Vector Index
print_step(4, 8, "Creating vector index")
try:
    s3vectors.create_index(
        vectorBucketName=vector_bucket_name,
        indexName=index_name,
        dataType="float32",
        dimension=dimension,
        distanceMetric="cosine",
        metadataConfiguration={
        'nonFilterableMetadataKeys': [
            'answer'
        ]
    }
    )
    print_success(f"Vector index created: {index_name}")
except ClientError as e:
    if 'already exists' in str(e).lower():
        print_success(f"Vector index already exists: {index_name}")
    else:
        exit_on_error(f"Failed to create vector index: {str(e)}")
except Exception as e:
    exit_on_error(f"Failed to create vector index: {str(e)}")


# Step 5: Create IAM policies and role
print_step(5, 8, "Creating IAM policies and execution role")

policies = [({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
            ],
            "Resource": [
                f"arn:aws:bedrock:{region}::foundation-model/{embedding_model}",
                f"arn:aws:bedrock:{region}::foundation-model/{generation_model}",
            ]
        }
    ]
}, "s3-vectors-bedrock-policy"),
({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [f'arn:aws:s3:::{bucket_name}', f'arn:aws:s3:::{bucket_name}/*'],
            "Condition": {
                "StringEquals": {
                    "aws:ResourceAccount": f"{account_id}"
                }
            }
        } 
    ]
}, "s3-vectors-s3-policy"),
({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3vectors:PutVectors",
                "s3vectors:GetVectors",
                "s3vectors:CreateIndex",
                "s3vectors:GetIndex",
                "s3vectors:QueryVectors"
            ],
            "Resource": [f'arn:aws:s3vectors:{region}:{account_id}:bucket/{vector_bucket_name}/index/{index_name}']
        } 
    ]
}, "s3-vectors-s3vectors-policy"),
({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"
            ],
            "Resource": "arn:aws:logs:*:*:log-group:/aws/bedrock/invokemodel:*"
        }
    ]
}, "s3-vectors-cw-policy"),]

assume_role_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

try:
    iam_client = session.client('iam')
    
    # Create execution role
    try:
        kb_execution_role = iam_client.create_role(
            RoleName=kb_role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description='Role for Amazon Bedrock Knowledge Bases'
        )
        print_success("IAM execution role created")
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            kb_execution_role = iam_client.get_role(RoleName=kb_role_name)
            print_success("IAM execution role already exists")
        else:
            raise e
    
    # Create and attach policies
    for policy_doc, name in policies:        
        try:
            iam_client.put_role_policy(
                RoleName=kb_role_name,
                PolicyName=name,
                PolicyDocument=json.dumps(policy_doc)
            )
            print_success(f"Policy attached: {name}")
        except ClientError as e:
            if 'already attached' in str(e).lower():
                print_success(f"Policy already attached: {name}")
            else:
                raise e
                
except Exception as e:
    exit_on_error(f"Failed to create IAM resources: {str(e)}")

# Step 6: Create Knowledge Base
print_step(6, 8, "Creating Bedrock Knowledge Base")
try:
    bedrock_agent_client = session.client('bedrock-agent')
    
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            kb_response = bedrock_agent_client.create_knowledge_base(
                name=kb_name,
                description="knowledge bases using s3 vectors",
                roleArn=kb_execution_role['Role']['Arn'],
                knowledgeBaseConfiguration={
                    'type': "VECTOR",
                    'vectorKnowledgeBaseConfiguration': {
                        'embeddingModelArn': f'arn:aws:bedrock:{region}::foundation-model/{embedding_model}'
                    }
                },
                storageConfiguration={
                    's3VectorsConfiguration': {
                        'indexArn': f'arn:aws:s3vectors:{region}:{account_id}:bucket/{vector_bucket_name}/index/{index_name}'
                    },
                    'type': 'S3_VECTORS'
                }
            )
            kb_id = kb_response["knowledgeBase"]["knowledgeBaseId"]
            break
        except ClientError as e:
            if 'ValidationException' in str(e) and 'role' in str(e).lower() and attempt < max_retries - 1:
                print_info(f"IAM role not yet ready, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                raise e

    kb_status = bedrock_agent_client.get_knowledge_base(
        knowledgeBaseId=kb_id
    )["knowledgeBase"]["status"]

    print_info("Waiting for Knowledge Base to be ready...")
    while kb_status == "CREATING":
        print_info(f"KB status: {kb_status} - waiting 10s...")
        time.sleep(10)
        kb_status = bedrock_agent_client.get_knowledge_base(
            knowledgeBaseId=kb_id
        )["knowledgeBase"]["status"]

    if kb_status == 'ACTIVE':
        print_success("Knowledge Base created successfully")
    else:
        exit_on_error(f"Knowledge Base creation failed with status: {kb_status}")

except Exception as e:
    exit_on_error(f"Failed to create Knowledge Base: {str(e)}")

# Step 7: Create Data Source
print_step(7, 8, "Creating Knowledge Base data source")
try:
    kb_data_source = bedrock_agent_client.create_data_source(
        knowledgeBaseId=kb_id,
        name=f'{kb_id}-s3',
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration":{
                "bucketArn": f"arn:aws:s3:::{bucket_name}"
            }
        },
        vectorIngestionConfiguration={
            "chunkingConfiguration": {
                "chunkingStrategy": "FIXED_SIZE",
                "fixedSizeChunkingConfiguration": {
                    "maxTokens": 100,
                    "overlapPercentage": 20
                }
            }
        },
        dataDeletionPolicy="RETAIN"
    )
    ds_id = kb_data_source["dataSource"]["dataSourceId"]
    print_success(f"Data source created: {ds_id}")
except Exception as e:
    exit_on_error(f"Failed to create data source: {str(e)}")

# Step 8: Start ingestion job
print_step(8, 8, "Starting data ingestion job")
try:
    start_job_response = bedrock_agent_client.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id
    )
    job = start_job_response["ingestionJob"]
    print_success(f"Ingestion job started: {job['ingestionJobId']}")
    
    print_info("Waiting for ingestion job to complete...")
    while job['status'] not in ["COMPLETE", "FAILED", "STOPPED"]:
        get_job_response = bedrock_agent_client.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job["ingestionJobId"]
        )
        job = get_job_response["ingestionJob"]
        print_info(f"Job status: {job['status']} - waiting 30s...")
        time.sleep(30)
    
    if job['status'] == 'COMPLETE':
        print_success("Data ingestion completed successfully")
    else:
        exit_on_error(f"Ingestion job failed with status: {job['status']}")
        
except Exception as e:
    exit_on_error(f"Failed to start or complete ingestion job: {str(e)}")

# Deployment completed
print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Deployment completed successfully!{Colors.END}")
print("=" * 50)
print_success(f"Knowledge Base ID: {kb_id}")
print_success(f"Data Source ID: {ds_id}")
print_success(f"S3 Bucket: {bucket_name}")
print_success(f"Vector Bucket: {vector_bucket_name}")
print_success(f"Vector Index: {index_name}")

with open("config.json", 'w') as f:
    json.dump({
        "region": region,
        "kb_id": kb_id,
        "ds_id": ds_id,
        "bucket_name": bucket_name,
        "vector_bucket_name": vector_bucket_name,
        "index_name": index_name,
        "embedding_model": embedding_model,
        "generation_model": generation_model
    }, f, indent=4)
