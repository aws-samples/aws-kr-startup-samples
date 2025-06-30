#!/usr/bin/env python3
import os
import boto3
import argparse
from pathlib import Path
from datetime import datetime
import uuid
import random

def generate_unique_id(user_id: str, style: str, gender: str) -> str:
    current_time = datetime.now().strftime("%Y%m%d%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{current_time}-{user_id}-{style}-{gender}-{unique_id}"

def upload_to_s3(bucket_name, file_name, s3_prefix, user_id, style, gender):
    """
    Upload a single file to S3 bucket
    
    Args:
        bucket_name (str): S3 bucket name
        file_name (str): Name of the file to upload
        s3_prefix (str): S3 prefix where file will be uploaded
        user_id (str): User ID
        style (str): Style name
        gender (str): Gender
    """
    s3_client = boto3.client('s3')
    
    # Check if user_id is empty
    if not user_id or user_id.strip() == "":
        print("Error: user_id cannot be empty")
        return
    
    # Get the absolute path of the file
    file_path = Path(file_name)
    if not file_path.exists():
        print(f"Error: File {file_name} does not exist")
        return
    
    # Generate unique ID and create S3 key
    unique_id = generate_unique_id(user_id, style, gender)
    s3_key = f"{s3_prefix}/{unique_id}.jpeg"
    
    try:
        with open(file_name, 'rb') as f:
            s3_client.put_object(Body=f.read(), Bucket=bucket_name, Key=s3_key)
        print(f"Successfully uploaded {file_name} to s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"Error uploading {file_name}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Upload a test image to S3')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--file-name', required=True, help='Name of the file to upload')
    parser.add_argument('--s3-prefix', default='images/generative-stylist/faces', 
                        help='S3 prefix where file will be uploaded')
    parser.add_argument('--user-id', required=True, help='User ID')
    parser.add_argument('--style', required=True, help='Style name')
    parser.add_argument('--gender', required=True, help='Gender')
    
    args = parser.parse_args()
    
    upload_to_s3(args.bucket, args.file_name, args.s3_prefix, args.user_id, args.style, args.gender)

if __name__ == "__main__":
    main() 