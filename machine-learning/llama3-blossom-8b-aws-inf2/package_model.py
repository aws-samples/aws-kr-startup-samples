import os
import tarfile
import boto3
import botocore.exceptions
from pathlib import Path

def package_model(model_dir: str, output_file: str):
    """Package model files into a tar.gz archive."""
    print(f"Packaging model from {model_dir} to {output_file}")
    
    with tarfile.open(output_file, 'w:gz') as tar:
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Get relative path from model_dir
                arcname = os.path.relpath(file_path, model_dir)
                print(f"Adding {file_path} as {arcname}")
                tar.add(file_path, arcname=arcname)
    
    print(f"Model packaged successfully: {output_file}")
    return output_file

def ensure_bucket_exists(bucket: str):
    """Create S3 bucket if it doesn't exist."""
    s3_client = boto3.client('s3')
    
    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=bucket)
        print(f"✅ Using existing S3 bucket: {bucket}")
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:  # NoSuchBucket
            print(f"📦 Creating S3 bucket: {bucket}")
            
            # Get current region
            session = boto3.Session()
            region = session.region_name or 'us-west-2'
            
            try:
                if region == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                
                # Enable versioning
                s3_client.put_bucket_versioning(
                    Bucket=bucket,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                
                # Add encryption
                s3_client.put_bucket_encryption(
                    Bucket=bucket,
                    ServerSideEncryptionConfiguration={
                        'Rules': [
                            {
                                'ApplyServerSideEncryptionByDefault': {
                                    'SSEAlgorithm': 'AES256'
                                }
                            }
                        ]
                    }
                )
                
                print(f"✅ S3 bucket created successfully: {bucket}")
            except Exception as e:
                print(f"❌ Failed to create bucket: {e}")
                raise
        else:
            print(f"❌ Error checking bucket: {e}")
            raise
    except Exception as e:
        print(f"❌ Error checking bucket: {e}")
        raise

def upload_to_s3(file_path: str, bucket: str, key: str):
    """Upload the packaged model to S3."""
    print(f"Uploading {file_path} to s3://{bucket}/{key}")
    
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(file_path, bucket, key)
        print(f"Upload successful: s3://{bucket}/{key}")
        return f"s3://{bucket}/{key}"
    except Exception as e:
        print(f"Upload failed: {e}")
        raise

def main():
    # Configuration
    model_dir = "models/llama3-blossom-8b"
    output_file = "model.tar.gz"
    # Get bucket name from environment or create default with current account ID
    bucket = os.environ.get("MODEL_BUCKET_NAME")
    if not bucket:
        # Get current account ID and region for default bucket name
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        session = boto3.Session()
        region = session.region_name or 'us-west-2'
        bucket = f"sagemaker-llm-{region}-{account_id}"
    s3_key = "inf2_model/model.tar.gz"
    
    # Check if model directory exists
    if not os.path.exists(model_dir):
        print(f"Error: Model directory {model_dir} does not exist")
        return
    
    # Package the model
    package_model(model_dir, output_file)
    
    # Ensure S3 bucket exists
    ensure_bucket_exists(bucket)
    
    # Upload to S3
    s3_uri = upload_to_s3(output_file, bucket, s3_key)
    
    # Clean up local tar file
    os.remove(output_file)
    print(f"Local tar file {output_file} removed")
    
    print(f"\nModel successfully packaged and uploaded!")
    print(f"S3 URI: {s3_uri}")
    print(f"\nUpdate your CDK configuration to use this S3 URI:")
    print(f"modelS3Uri: '{s3_uri}'")

if __name__ == "__main__":
    main()
