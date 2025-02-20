import random
import boto3
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables safely (add appropriate exception handling if needed)
MODEL_ID = os.environ.get('MODEL_ID')
S3_DESTINATION_BUCKET = os.environ.get('S3_DESTINATION_BUCKET')
VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME = os.environ.get('VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')  # Default region setting for Amazon Nova Reel

ddb_client = boto3.client('dynamodb')

def create_response(status_code, body):
    """
    Unified function for generating HTTP responses.
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
    If the body is a string, parse it as JSON; if it's already a dict, return it directly.
    Return None if a parsing error occurs.
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

def lambda_handler(event, context):
    logger.info("Received event: %s", event)
    http_method = event.get('httpMethod', '')
    
    if http_method == 'OPTIONS':
        return create_response(200, {})
    
    if http_method != 'POST':
        return create_response(405, {'error': f"{http_method} Methods are not allowed."})
        
    # Parse and validate the request body
    body = event.get('body')
    parsed_body = parse_body(body)
    if not parsed_body:
        return create_response(400, {'error': 'Bad Request: A valid body is required.'})
        
    prompt = parsed_body.get('prompt')
    if not prompt:
        return create_response(400, {'error': 'Bad Request: prompt field is required.'})
        
    logger.info("Received prompt: %s", prompt)
    
    bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    
    model_input = {
        "taskType": "TEXT_VIDEO",
        "textToVideoParams": {"text": prompt},
        "videoGenerationConfig": {
            "durationSeconds": 6,
            "fps": 24,
            "dimension": "1280x720",
            "seed": random.randint(0, 2147483648)
        }
    }
    
    try:
        invocation = bedrock_runtime.start_async_invoke(
            modelId=MODEL_ID,
            modelInput=model_input,
            outputDataConfig={"s3OutputDataConfig": {"s3Uri": f"s3://{S3_DESTINATION_BUCKET}"}}
        )
    except Exception as e:
        logger.error("Bedrock asynchronous invocation error: %s", e)
        return create_response(500, {'error': 'Server error: Failed to initiate video generation request.'})
    
    invocation_arn = invocation.get("invocationArn")
    invocation_id = invocation_arn.split('/')[-1]
    
    print("Invocation ARN:", invocation_arn)
    print("Invocation ID:", invocation_id)

    if not invocation_arn:
        logger.error("invocationArn missing")
        return create_response(500, {'error': 'Server error: Failed to initiate video generation request.'})
        
    s3_prefix = invocation_arn.split('/')[-1]
    s3_location = f"s3://{S3_DESTINATION_BUCKET}/{s3_prefix}"

    # Save the invocation ARN to the DynamoDB table
    response = ddb_client.put_item(
        TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
        Item={
            'invocation_id': {"S": invocation_id},
            'invocation_arn': {"S": invocation_arn},
            'prompt': {"S": prompt},
            'status': {"S": 'InProgress'},
            'location': {"S": s3_location},
            'updated_at': {"S": datetime.now().isoformat()},
            'created_at': {"S": datetime.now().isoformat()}
        }
    )
    
    return create_response(200, {
        'message': 'Video generation started',
        'invocationArn': invocation_arn,
        'location': f"{s3_location}/output.mp4"
    })