import boto3
import json
import os
import logging
from boto3.dynamodb.types import TypeDeserializer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME = os.environ.get('VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME')

ddb_client = boto3.client('dynamodb')
s3_client = boto3.client('s3')

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
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        }
    }

def lambda_handler(event, context):
    logger.info("Received event: %s", event)
    http_method = event.get('httpMethod', '')
    
    if http_method == 'OPTIONS':
        return create_response(200, {})
    
    if http_method != 'GET':
        return create_response(405, {'error': f"{http_method} Methods are not allowed."})
    
    path_parameters = event.get('pathParameters', {}) or {}
    invocation_id = path_parameters.get('invocation_id')
    
    if not invocation_id:
        return create_response(400, {'error': 'invocation_id is required'})
    
    try:
        query_response = ddb_client.query(
            TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
            KeyConditionExpression="invocation_id = :id",
            ExpressionAttributeValues={
                ":id": {"S": invocation_id}
            }
        )
        
        if not query_response.get('Items'):
            return create_response(404, {'error': 'Video not found'})
        
        item_data = query_response['Items'][0]
        deserializer = TypeDeserializer()
        item = {k: deserializer.deserialize(v) for k, v in item_data.items()}
        
        if 'location' in item:
            s3_url = item['location']
            
            parts = s3_url.split('/')
            bucket = parts[2]
            
            key = f"{invocation_id}/output.mp4"
            
            try:
                s3_client.head_object(Bucket=bucket, Key=key)
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=300
                )
                
                item['presigned_url'] = presigned_url
                logger.info(f"Generated presigned URL for s3://{bucket}/{key}")
            except Exception as s3_error:
                logger.error(f"Error accessing S3 object: {s3_error}")
        else:
            logger.warning(f"No location field for invocation_id: {invocation_id}")
        
        return create_response(200, item)
        
    except Exception as e:
        logger.error("Error fetching video: %s", e)
        return create_response(500, {'error': 'Internal server error'})