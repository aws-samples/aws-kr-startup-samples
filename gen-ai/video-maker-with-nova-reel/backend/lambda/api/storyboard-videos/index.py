import random
import boto3
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
MODEL_ID = os.environ.get('MODEL_ID')
S3_DESTINATION_BUCKET = os.environ.get('S3_DESTINATION_BUCKET')
VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME = os.environ.get('VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME')
AWS_REGION = 'us-east-1'  # Amazon Nova Reel default region

ddb_client = boto3.client('dynamodb')
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

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

def generate_video(prompt, storyboard_id):
    """
    Function for generating a single video
    """
    model_input = {
        "taskType": "TEXT_VIDEO",
        "textToVideoParams": {
            "text": prompt
        },
        "videoGenerationConfig": {
            "durationSeconds": 6,
            "fps": 24,
            "dimension": "1280x720",
            "seed": random.randint(0, 2147483646)
        }
    }
    
    try:
        invocation = bedrock_runtime.start_async_invoke(
            modelId=MODEL_ID,
            modelInput=model_input,
            outputDataConfig={"s3OutputDataConfig": {"s3Uri": f"s3://{S3_DESTINATION_BUCKET}"}}
        )
    except Exception as e:
        logger.error("Bedrock async invocation error: %s", e)
        raise e
    
    invocation_arn = invocation.get("invocationArn")
    invocation_id = invocation_arn.split('/')[-1]
    
    logger.info("Invocation ARN: %s", invocation_arn)
    logger.info("Invocation ID: %s", invocation_id)

    if not invocation_arn:
        logger.error("invocationArn missing")
        raise Exception("Failed to initiate video generation request.")
        
    s3_prefix = invocation_arn.split('/')[-1]
    s3_location = f"s3://{S3_DESTINATION_BUCKET}/{s3_prefix}/output.mp4"

    # Save video generation information to DynamoDB
    ddb_client.put_item(
        TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
        Item={
            'invocation_id': {"S": invocation_id},
            'invocation_arn': {"S": invocation_arn},
            'prompt': {"S": prompt},
            'status': {"S": 'InProgress'},
            'location': {"S": s3_location},
            'storyboard_id': {"S": storyboard_id},
            'updated_at': {"S": datetime.now().isoformat()},
            'created_at': {"S": datetime.now().isoformat()}
        }
    )
    
    return invocation_id

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
        
    storyboard = parsed_body.get('storyboard')
    if not storyboard or not storyboard.get('scenes'):
        return create_response(400, {'error': 'Invalid request: storyboard field and scenes array are required.'})
    
    # Generate storyboard ID (timestamp + random number)
    storyboard_id = f"sb_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
    
    # Generate videos for each scene
    invocation_ids = []
    try:
        for scene in storyboard.get('scenes'):
            prompt = scene.get('prompt')
            if not prompt:
                continue
                
            invocation_id = generate_video(prompt, storyboard_id)
            invocation_ids.append(invocation_id)
    except Exception as e:
        logger.error("Video generation error: %s", e)
        return create_response(500, {'error': f'Server error: Failed to generate videos. {str(e)}'})
    
    return create_response(200, {
        'message': 'Storyboard video generation has been initiated.',
        'storyboard_id': storyboard_id,
        'invocationIds': invocation_ids
    })