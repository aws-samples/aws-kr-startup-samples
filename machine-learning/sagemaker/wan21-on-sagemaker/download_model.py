#!/usr/bin/env python3
import os
import sys
import boto3
import logging
import argparse
import subprocess
import tempfile
import shutil
import tarfile
from pathlib import Path

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='Download Wan2.1 model and upload to S3')
    parser.add_argument('--model-name', type=str, default='Wan-AI/Wan2.1-T2V-14B',
                        help='Hugging Face model name to download (default: Wan-AI/Wan2.1-T2V-14B)')
    parser.add_argument('--bucket-name', type=str, required=True,
                        help='S3 bucket name to upload the model')
    parser.add_argument('--s3-key', type=str, default='models/wan2.1-t2v-14b/model.tar.gz',
                        help='S3 key for the uploaded model file (default: models/wan2.1-t2v-14b/model.tar.gz)')
    parser.add_argument('--region', type=str, default='us-east-1',
                        help='AWS region (default: us-east-1)')
    return parser.parse_args()

def download_model(model_name, download_dir):
    """Download model from Hugging Face"""
    cmd = f"huggingface-cli download {model_name} --local-dir {download_dir}"
    subprocess.run(cmd, shell=True, check=True)
    return True

def create_tarfile(source_dir, output_file):
    """Compress model directory to tar.gz file"""
    with tarfile.open(output_file, "w:gz") as tar:
        for file_path in Path(source_dir).rglob('*'):
            if file_path.is_file():
                arcname = str(file_path.relative_to(Path(source_dir).parent))
                tar.add(file_path, arcname=arcname)
    return True

def upload_to_s3(file_path, bucket_name, s3_key, region):
    """Upload compressed model file to S3 using multipart upload"""
    s3_client = boto3.client('s3', region_name=region)
    file_size = os.path.getsize(file_path)
    chunk_size = 100 * 1024 * 1024  # 100MB
    if file_size > chunk_size:
        response = s3_client.create_multipart_upload(
            Bucket=bucket_name,
            Key=s3_key
        )
        upload_id = response['UploadId']
        parts = []
        part_number = 1
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                part_response = s3_client.upload_part(
                    Bucket=bucket_name,
                    Key=s3_key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=chunk
                )
                parts.append({
                    'ETag': part_response['ETag'],
                    'PartNumber': part_number
                })
                part_number += 1
        s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=s3_key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
    else:
        s3_client.upload_file(file_path, bucket_name, s3_key)
    model_url = f"s3://{bucket_name}/{s3_key}"
    return model_url

def main():
    args = parse_args()
    with tempfile.TemporaryDirectory() as temp_dir:
        model_dir = os.path.join(temp_dir, os.path.basename(args.model_name))
        download_model(args.model_name, model_dir)
        tar_file = os.path.join(temp_dir, "model.tar.gz")
        create_tarfile(model_dir, tar_file)
        model_url = upload_to_s3(tar_file, args.bucket_name, args.s3_key, args.region)
        print(f"MODEL_DATA_URL={model_url}")

if __name__ == "__main__":
    main()