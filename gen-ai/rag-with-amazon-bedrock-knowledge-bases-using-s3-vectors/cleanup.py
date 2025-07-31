import boto3
import time
import argparse
from botocore.exceptions import ClientError
from utils import Colors, print_step, print_success, print_info, exit_on_error, load_config

# Load configuration
config = load_config()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Cleanup S3 Vector RAG resources')
parser.add_argument('--auto-approval', action='store_true', help='Skip confirmation prompt and proceed automatically')
args = parser.parse_args()

region = config['region']
kb_id = config['kb_id']
ds_id = config['ds_id']
auto_approval = args.auto_approval

# Account settings
print(f"{Colors.BOLD}Starting AWS Resource Cleanup{Colors.END}")
print("=" * 50)

try:
    session = boto3.session.Session(region_name=region)
    account_id = session.client("sts").get_caller_identity()["Account"]
    print_info(f"Account ID: {account_id}")
    print_info(f"Region: {region}")
    print_info(f"Knowledge Base ID: {kb_id}")
    print_info(f"Data Source ID: {ds_id}")
except Exception as e:
    exit_on_error(f"Failed to get AWS credentials: {str(e)}")

bucket_name = f's3-vectors-{account_id}-{region}-faqs'
vector_bucket_name = f's3-vectors-{account_id}-{region}-embeddings'
index_name = "s3-vectors-index"

# Show resources to be deleted
print("\nResources to be deleted:")
print_info(f"Knowledge Base: {kb_id}")
print_info(f"Data Source: {ds_id}")
print_info("IAM Role: s3-vectors-kb-execution-role")
print_info(f"Vector Bucket: {vector_bucket_name}")
print_info(f"Vector Index: {index_name}")
print_info(f"S3 Bucket: {bucket_name}")

# Ask for confirmation
if not auto_approval:
    confirm = input(f"\nDo you want to proceed with cleanup? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cleanup cancelled.")
        exit(0)
else:
    print("\nAuto-approval enabled. Proceeding with cleanup...")

# Step 1: Delete Data Source
print_step(1, 6, "Deleting Knowledge Base data source")
try:
    bedrock_agent_client = session.client('bedrock-agent')
    bedrock_agent_client.delete_data_source(
        dataSourceId=ds_id,
        knowledgeBaseId=kb_id
    )
    print_success(f"Data source deleted: {ds_id}")
except ClientError as e:
    if e.response['Error']['Code'] in ['ResourceNotFoundException', 'ValidationException']:
        print_success(f"Data source not found or already deleted: {ds_id}")
    else:
        exit_on_error(f"Failed to delete data source: {str(e)}")
except Exception as e:
    exit_on_error(f"Failed to delete data source: {str(e)}")

# Step 2: Delete Knowledge Base
print_step(2, 6, "Deleting Knowledge Base")
try:
    kb_response = bedrock_agent_client.delete_knowledge_base(
        knowledgeBaseId=kb_id
    )
    status = kb_response["status"]
    print_success(f"Knowledge Base deletion initiated: {kb_id}")
    
    print_info("Waiting for Knowledge Base deletion to complete...")
    while status in ["ACTIVE", "DELETING", "UPDATING"]:
        print_info(f"KB status: {status} - waiting 30s...")
        time.sleep(30)
        
        try:
            kb_response = bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=kb_id
            )
            status = kb_response["knowledgeBase"]["status"]
        except bedrock_agent_client.exceptions.ResourceNotFoundException:
            print_success("Knowledge Base deleted successfully")
            break
except ClientError as e:
    if e.response['Error']['Code'] in ['ResourceNotFoundException', 'ValidationException']:
        print_success(f"Knowledge Base not found or already deleted: {kb_id}")
    else:
        exit_on_error(f"Failed to delete Knowledge Base: {str(e)}")
except Exception as e:
    exit_on_error(f"Failed to delete Knowledge Base: {str(e)}")


# Step 3: Delete IAM Role and Policies
print_step(3, 6, "Deleting IAM role and policies")
try:
    kb_role_name = 's3-vectors-kb-execution-role'
    iam_client = session.client("iam")
    
    # Detach and delete policies
    try:
        policies = iam_client.list_role_policies(RoleName=kb_role_name)["PolicyNames"]
        for policy in policies:
            iam_client.delete_role_policy(
                RoleName=kb_role_name,
                PolicyName=policy
            )
            
            print_success(f"Policy deleted: {policy}")
        
        # Delete role
        iam_client.delete_role(RoleName=kb_role_name)
        print_success(f"IAM role deleted: {kb_role_name}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print_success("IAM role already deleted or does not exist")
        else:
            raise e
except Exception as e:
    exit_on_error(f"Failed to delete IAM resources: {str(e)}")


# Step 4: Delete S3 Vector Storage
print_step(4, 6, "Deleting S3 Vector Storage")
try:
    s3vectors = session.client('s3vectors')
    
    # Delete vector index
    try:
        s3vectors.delete_index(vectorBucketName=vector_bucket_name, indexName=index_name)
        print_success(f"Vector index deleted: {index_name}")
    except ClientError as e:
        if 'NotFound' in str(e) or 'does not exist' in str(e).lower():
            print_success(f"Vector index not found or already deleted: {index_name}")
        else:
            print_info(f"Could not delete vector index: {str(e)}")
    except Exception as e:
        print_info(f"Could not delete vector index: {str(e)}")
    
    # Delete vector bucket
    try:
        s3vectors.delete_vector_bucket(vectorBucketName=vector_bucket_name)
        print_success(f"Vector bucket deleted: {vector_bucket_name}")
    except ClientError as e:
        if 'NotFound' in str(e) or 'does not exist' in str(e).lower():
            print_success(f"Vector bucket not found or already deleted: {vector_bucket_name}")
        else:
            print_info(f"Could not delete vector bucket: {str(e)}")
    except Exception as e:
        print_info(f"Could not delete vector bucket: {str(e)}")
except Exception as e:
    exit_on_error(f"Failed to delete vector storage: {str(e)}")


# Step 5: Delete S3 Bucket
print_step(5, 6, "Deleting S3 bucket")
try:
    s3 = session.client('s3')
    
    # Delete all objects in bucket
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={
                    'Objects': [
                        {'Key': obj['Key']} for obj in response['Contents']
                    ]
                }
            )
            print_success(f"All objects deleted from bucket: {bucket_name}")
        else:
            print_success("Bucket is already empty")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print_success(f"S3 bucket not found or already deleted: {bucket_name}")
        else:
            raise e
    
    # Delete bucket
    try:
        s3.delete_bucket(Bucket=bucket_name)
        print_success(f"S3 bucket deleted: {bucket_name}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print_success(f"S3 bucket not found or already deleted: {bucket_name}")
        else:
            raise e
except Exception as e:
    exit_on_error(f"Failed to delete S3 bucket: {str(e)}")

# delete config.json from local directory
print_step(6, 6, "Deleting config.json")
try:
    import os
    os.remove('config.json')
    print_success("config.json deleted successfully")
except Exception as e:
    print_info(f"Could not delete config.json: {str(e)}")
    print_info("Please delete config.json manually")


# Cleanup completed
print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Cleanup completed successfully!{Colors.END}")
print("=" * 50)
print_success("All resources have been deleted")
