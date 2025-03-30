import boto3
import json
import os
import logging
import uuid
import time
from datetime import datetime
import tempfile
import subprocess
import shutil

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
S3_DESTINATION_BUCKET = os.environ.get('S3_DESTINATION_BUCKET')
VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME = os.environ.get('VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME')
AWS_REGION = 'us-east-1'

# Initialize AWS clients
ddb_client = boto3.client('dynamodb')
s3_client = boto3.client('s3')

def create_response(status_code, body):
    """
    Integrated HTTP response generation function
    """
    return {
        'statusCode': status_code,
        'body': json.dumps(body),
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        }
    }

def parse_body(body):
    """
    Parse as JSON if it's a string, return as is if it's already a dict
    Return None if parsing error occurs
    """
    if not body:
        return None
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            logger.error("JSON parsing error: %s", e)
            return None
    return body

def download_videos(invocation_ids, temp_dir):
    """
    Download videos from S3 and return a list of local paths
    """
    video_paths = []
    
    for invocation_id in invocation_ids:
        # Look up video information in DynamoDB
        response = ddb_client.get_item(
            TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
            Key={'invocation_id': {'S': invocation_id}}
        )
        
        if 'Item' not in response:
            logger.error(f"Video information not found: {invocation_id}")
            continue
            
        video_item = response['Item']
        status = video_item.get('status', {}).get('S')
        
        if status != 'Completed':
            logger.error(f"Video not yet completed: {invocation_id}, status: {status}")
            continue
            
        # Parse S3 path
        s3_location = video_item.get('location', {}).get('S', '')
        if not s3_location or not s3_location.startswith('s3://'):
            logger.error(f"Invalid S3 path: {s3_location}")
            continue
            
        # Extract bucket and key from s3://bucket/key format
        s3_parts = s3_location[5:].split('/', 1)
        if len(s3_parts) != 2:
            logger.error(f"Failed to parse S3 path: {s3_location}")
            continue
            
        bucket = s3_parts[0]
        key = s3_parts[1]
        
        # Path to save the video file
        local_path = os.path.join(temp_dir, f"{invocation_id}.mp4")
        
        try:
            logger.info(f"Attempting to download video from S3: s3://{bucket}/{key}")
            # Download video from S3
            s3_client.download_file(bucket, key, local_path)
            video_paths.append(local_path)
            logger.info(f"Video download successful: {local_path}")
        except Exception as e:
            logger.error(f"Video download failed: {invocation_id}, error: {str(e)}")
    
    return video_paths

def create_video_list_file(video_paths, temp_dir):
    """
    Create an FFmpeg input file list
    """
    list_path = os.path.join(temp_dir, "video_list.txt")
    with open(list_path, 'w') as f:
        for path in video_paths:
            f.write(f"file '{path}'\n")
    return list_path

def merge_videos_with_ffmpeg(video_list_file, output_path):
    """
    Merge videos using FFmpeg
    """
    try:
        command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", video_list_file,
            "-c", "copy",  # Copy without re-encoding
            output_path
        ]
        
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=True
        )
        
        logger.info(f"FFmpeg execution result: {result.stdout.decode()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg execution failed: {e.stderr.decode()}")
        return False

def upload_merged_video(local_path, s3_key):
    """
    Upload the merged video to S3
    """
    try:
        s3_client.upload_file(local_path, S3_DESTINATION_BUCKET, s3_key)
        return f"s3://{S3_DESTINATION_BUCKET}/{s3_key}"
    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        return None

def lambda_handler(event, context):
    logger.info("Received event: %s", event)
    http_method = event.get('httpMethod', '')
    
    if http_method == 'OPTIONS':
        return create_response(200, {})
    
    if http_method != 'POST':
        return create_response(405, {'error': f"{http_method} method is not allowed."})
        
    # Parse and validate request body
    body = event.get('body')
    parsed_body = parse_body(body)
    if not parsed_body:
        return create_response(400, {'error': 'Invalid request: Valid body is required.'})
        
    invocation_ids = parsed_body.get('invocationIds')
    if not invocation_ids or not isinstance(invocation_ids, list) or len(invocation_ids) < 2:
        return create_response(400, {'error': 'Invalid request: At least 2 invocationIds are required.'})
    
    # Create temporary directory for merging operation
    temp_dir = tempfile.mkdtemp()
    merged_id = f"merged_{int(datetime.now().timestamp())}_{str(uuid.uuid4())[:8]}"
    merged_output_path = os.path.join(temp_dir, f"{merged_id}.mp4")
    s3_key = f"merged/{merged_id}/output.mp4"
    
    try:
        # Download videos
        video_paths = download_videos(invocation_ids, temp_dir)
        if len(video_paths) < 2:
            return create_response(400, {'error': 'Less than 2 videos available for merging. Verify that all videos are in completed status.'})
        
        # Create video list file
        video_list_file = create_video_list_file(video_paths, temp_dir)
        
        # Merge videos with FFmpeg
        if not merge_videos_with_ffmpeg(video_list_file, merged_output_path):
            return create_response(500, {'error': 'Video merging failed'})
        
        # Upload merged video to S3
        s3_location = upload_merged_video(merged_output_path, s3_key)
        if not s3_location:
            return create_response(500, {'error': 'Failed to upload merged video'})
        
        # Save merge information to DynamoDB
        merged_sources = ",".join(invocation_ids)
        ddb_client.put_item(
            TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
            Item={
                'invocation_id': {"S": merged_id},
                'invocation_arn': {"S": f"merged/{merged_id}"},
                'prompt': {"S": f"Merged video from {len(invocation_ids)} sources: {merged_sources}"},
                'status': {"S": 'Completed'},
                'location': {"S": s3_location},
                'merged_from': {"S": merged_sources},
                'updated_at': {"S": datetime.now().isoformat()},
                'created_at': {"S": datetime.now().isoformat()}
            }
        )
        
    except Exception as e:
        logger.error(f"Error occurred during merge processing: {str(e)}")
        return create_response(500, {'error': f'Video merge failed: {str(e)}'})
    finally:
        # Clean up temporary files
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to delete temporary files: {str(e)}")
    
    return create_response(200, {
        'message': 'Video merge completed',
        'merged_id': merged_id,
        'location': s3_location
    })