import random
import boto3
import json
import os
import logging
from datetime import datetime
from botocore.exceptions import ClientError # Import ClientError for exception handling

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
MODEL_ID = os.environ.get('MODEL_ID')
S3_DESTINATION_BUCKET = os.environ.get('S3_DESTINATION_BUCKET')
VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME = os.environ.get('VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME')
AWS_REGION = 'us-east-1'  # Default region for Nova Reel

# Environment variables for scheduled runs (from CDK)
SCHEDULE_PROMPT_PARAM_NAME = os.environ.get('SCHEDULE_PROMPT_PARAM_NAME')
SCHEDULE_ENABLED_PARAM_NAME = os.environ.get('SCHEDULE_ENABLED_PARAM_NAME')

ddb_client = boto3.client('dynamodb')
ssm_client = boto3.client('ssm') # Initialize SSM client
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

def create_response(status_code, body):
    """Unified function for generating HTTP responses."""
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
    """Parses JSON body from API Gateway event."""
    if not body:
        return None
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return None
    return body

def get_scheduled_prompt():
    """Gets the prompt from SSM for scheduled runs, checking if enabled."""
    try:
        # Check if scheduling is enabled
        enabled_param = ssm_client.get_parameter(Name=SCHEDULE_ENABLED_PARAM_NAME)
        is_enabled = enabled_param['Parameter']['Value'].lower() == 'true'

        if not is_enabled:
            logger.info("Scheduled video generation is disabled via SSM parameter.")
            return None # Return None if disabled

        # Get the prompt if enabled
        prompt_param = ssm_client.get_parameter(Name=SCHEDULE_PROMPT_PARAM_NAME)
        prompt = prompt_param['Parameter']['Value']
        logger.info(f"Using scheduled prompt from SSM: '{prompt}'")
        return prompt

    except ClientError as e:
        logger.error(f"Error getting schedule parameters from SSM: {e}")
        return None # Return None on error
    except Exception as e: # Catch other potential errors
        logger.error(f"Unexpected error getting scheduled prompt: {e}")
        return None

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    prompt = None
    num_shots = 2 # Default value
    image_data = None
    image_format = 'jpeg'
    is_scheduled_run = False
    invocation_source = "API Gateway"

    # Determine the invocation source (API Gateway vs. Scheduler)
    if 'source' in event and event['source'] == 'aws.scheduler.manage-video-schedule':
        logger.info("Invocation detected from EventBridge Scheduler.")
        is_scheduled_run = True
        invocation_source = "Scheduler"
        try:
            # Scheduler가 전달한 Input은 event 객체 자체가 됨
            prompt = event.get('prompt')
            if not prompt:
                 logger.error("Prompt missing in scheduled event payload.")
                 # 스케줄된 실행 실패 처리 (오류 로깅 후 종료)
                 return {'statusCode': 400, 'body': 'Bad Request: Prompt missing in scheduled event'}
            logger.info(f"[Scheduler] Using prompt: '{prompt}'")
            # 스케줄 실행 시 num_shots, image 등은 기본값 사용 또는 고정
            num_shots = 2 # 예시: 스케줄은 2샷 고정
        except Exception as e:
             logger.error(f"Error parsing scheduled event payload: {e}")
             return {'statusCode': 500, 'body': 'Error processing scheduled event'}

    elif 'httpMethod' in event:
        logger.info("Invocation detected from API Gateway.")
        http_method = event['httpMethod']

        if http_method == 'OPTIONS':
            return create_response(200, {})

        if http_method != 'POST':
            return create_response(405, {'error': f"{http_method} Methods are not allowed."})

        # Parse request body for API Gateway calls
        body = event.get('body')
        parsed_body = parse_body(body)
        if not parsed_body:
            return create_response(400, {'error': 'Bad Request: A valid body is required.'})

        prompt = parsed_body.get('prompt')
        if not prompt:
            return create_response(400, {'error': 'Bad Request: prompt field is required.'})

        # Get optional parameters from API Gateway request
        num_shots = parsed_body.get('num_shots', 2)
        image_data = parsed_body.get('image_data')
        image_format = parsed_body.get('image_format', 'jpeg')
        logger.info(f"[API Gateway] Using prompt: '{prompt}', shots: {num_shots}")

    else:
        logger.warning("Invocation source not recognized (neither Scheduler nor API Gateway POST/OPTIONS).")
        return {'statusCode': 400, 'body': json.dumps({'error': 'Unrecognized invocation source.'})}

    # --- Common logic for video generation --- 

    durationSeconds = max(int(num_shots) * 6, 12) # Ensure num_shots is int

    # Construct Bedrock model input
    model_input = {
        "taskType": "MULTI_SHOT_AUTOMATED",
        "multiShotAutomatedParams": {
            "text": prompt
        },
        "videoGenerationConfig": {
            "durationSeconds": durationSeconds,
            "fps": 24,
            "dimension": "1280x720",
            "seed": random.randint(0, 2147483648)
        }
    }

    # Add image data only if provided (will only happen via API Gateway)
    if not is_scheduled_run and image_data:
        logger.info("Image data provided, adding to Bedrock input.")
        model_input["multiShotAutomatedParams"]["images"] = [
            {
                "format": image_format,
                "source": {
                    "bytes": image_data
                }
            }
        ]
    
    logger.info(f"Initiating Bedrock async invocation (Source: {invocation_source}) with prompt: '{prompt}'")
    try:
        invocation = bedrock_runtime.start_async_invoke(
            modelId=MODEL_ID,
            modelInput=model_input,
            outputDataConfig={"s3OutputDataConfig": {"s3Uri": f"s3://{S3_DESTINATION_BUCKET}"}}
        )
    except ClientError as e:
        logger.error(f"Bedrock asynchronous invocation error: {e}")
        # For scheduled runs, we might not want to return an API Gateway response
        # For API Gateway, return error response
        if not is_scheduled_run:
             return create_response(500, {'error': f'Server error: Failed to initiate video generation request. {str(e)}'})
        else:
             # Log error for scheduled run, no HTTP response needed
             raise e # Re-raise to indicate Lambda failure if desired
    except Exception as e: # Catch other potential errors
         logger.error(f"Unexpected error during Bedrock invocation: {e}")
         if not is_scheduled_run:
             return create_response(500, {'error': 'Server error: Unexpected error during video generation.'})
         else:
             raise e

    invocation_arn = invocation.get("invocationArn")
    if not invocation_arn:
        logger.error("invocationArn missing from Bedrock response.")
        if not is_scheduled_run:
            return create_response(500, {'error': 'Server error: Failed to get invocation ARN.'})
        else:
            # Log error, maybe raise exception
            return # Exit gracefully for scheduled run

    invocation_id = invocation_arn.split('/')[-1]
    logger.info(f"Bedrock Invocation ARN: {invocation_arn}")
    logger.info(f"Bedrock Invocation ID: {invocation_id}")

    s3_prefix = invocation_id # The prefix in S3 matches the invocation ID
    # Note: The actual output file name might vary (e.g., output.mp4), status check lambda handles final location.
    s3_base_location = f"s3://{S3_DESTINATION_BUCKET}/{s3_prefix}"

    # Save metadata to DynamoDB
    try:
        ddb_client.put_item(
            TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
            Item={
                'invocation_id': {"S": invocation_id},
                'invocation_arn': {"S": invocation_arn},
                'prompt': {"S": prompt},
                'status': {"S": 'InProgress'},
                'location': {"S": s3_base_location}, # Store base location
                'source': {"S": invocation_source}, # 호출 소스 기록
                'updated_at': {"S": datetime.now().isoformat()},
                'created_at': {"S": datetime.now().isoformat()}
            }
        )
        logger.info(f"Successfully saved invocation details to DynamoDB for ID: {invocation_id}")
    except ClientError as e:
        logger.error(f"DynamoDB put_item error: {e}")
        # Handle error appropriately, maybe retry or raise
        if not is_scheduled_run:
            # Optionally return error for API Gateway call
            return create_response(500, {'error': 'Failed to save invocation details.'})
        else:
            # Log for scheduled run
             pass # Or raise e

    # Return response only for API Gateway calls
    if not is_scheduled_run:
        return create_response(200, {
            'message': 'Video generation started',
            'invocationId': invocation_id, # Return ID instead of ARN
            'invocationArn': invocation_arn,
            'locationHint': f"{s3_base_location}/output.mp4" # Hint for potential location
        })
    else:
        # Log success for scheduled run
        logger.info("Scheduled video generation initiated successfully.")
        return {'statusCode': 200, 'body': json.dumps({'message': 'Scheduled video generation initiated.'})}