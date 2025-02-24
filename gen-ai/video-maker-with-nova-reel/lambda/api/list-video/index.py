import random
import boto3
import json
import os
import logging
import base64
from boto3.dynamodb.types import TypeDeserializer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME = os.environ.get('VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME')
ddb_client = boto3.client('dynamodb')

def lambda_handler(event, context):
    """
    Main handler for the Lambda function that processes GET requests for video listings.
    Includes functionality to update video statuses and retrieve paginated, sorted video lists.
    """
    logger.info("Received event: %s", event)
    
    # Handle CORS and method validation
    http_method = event.get('httpMethod', '')
    if http_method == 'OPTIONS':
        return create_http_response(200, {})
    if http_method != 'GET':
        return create_http_response(405, {'error': f"{http_method} Methods are not allowed."})

    # Update status of in-progress videos
    try:
        update_video_statuses()
    except Exception as e:
        logger.error(f"Error updating video statuses: {e}")
        return create_http_response(500, {'error': 'Failed to update video statuses'})

    # Extract and validate query parameters
    query_params = event.get("queryStringParameters") or {}
    logger.info("Query params: %s", query_params)
    
    # Parse pagination and sorting parameters
    sort_params = {
        'sort_key': query_params.get("sort", "created_at"),
        'sort_order': query_params.get("order", "desc")
    }
    
    try:
        limit = int(query_params.get("limit")) if "limit" in query_params else None
    except ValueError:
        logger.error("Invalid limit value: %s", query_params.get("limit"))
        limit = None

    # Handle pagination token
    exclusive_start_key = None
    if next_token := query_params.get("nextToken"):
        try:
            exclusive_start_key = json.loads(base64.b64decode(next_token).decode('utf-8'))
        except Exception as e:
            logger.error(f"Invalid nextToken value: {next_token}, error: {e}")
            return create_http_response(400, {'error': 'Invalid pagination token'})

    # Retrieve and return video list
    try:
        data = get_video_list(limit, exclusive_start_key, **sort_params)
        return create_http_response(200, data)
    except Exception as e:
        logger.error(f"Error retrieving video list: {e}")
        return create_http_response(500, {'error': 'Failed to retrieve video list'})

def create_http_response(status_code, body):
    """
    Creates a standardized HTTP response with CORS headers
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

def update_video_statuses():
    """
    Updates the status of videos marked as 'InProgress' by checking their current state in Bedrock
    """
    response = ddb_client.scan(
        TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
        FilterExpression='#status = :status',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':status': {'S': 'InProgress'}}
    )
    
    items = response.get('Items', [])
    logger.info(f"Number of in-progress items: {len(items)}")
    
    bedrock_runtime = boto3.client('bedrock-runtime')
    
    for item in items:
        invocation_arn = item.get('invocation_arn', {}).get('S')
        invocation_id = item.get('invocation_id', {}).get('S')
        
        if not (invocation_arn and invocation_id):
            continue
            
        try:
            status_response = bedrock_runtime.get_async_invoke(invocationArn=invocation_arn)
            current_status = status_response.get('status')
            
            if current_status in ['Completed', 'Failed']:
                new_status = 'Completed' if current_status == 'Completed' else 'Failed'
                s3_uri = status_response.get('outputDataConfig', {}).get('s3OutputDataConfig', {}).get('s3Uri') if new_status == 'Completed' else None
                
                ddb_client.update_item(
                    TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
                    Key={'invocation_id': {'S': invocation_id}},
                    UpdateExpression='SET #status = :status, s3_uri = :s3_uri',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': {'S': new_status},
                        ':s3_uri': {'S': s3_uri} if s3_uri else {'NULL': True}
                    }
                )
        except Exception as e:
            logger.error(f"Error checking status for invocation_id {invocation_id}: {e}")

def get_video_list(limit=None, exclusive_start_key=None, sort_key="created_at", sort_order="desc"):
    """
    Retrieves and returns a sorted, paginated list of videos from DynamoDB
    """
    scan_kwargs = {"TableName": VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME}
    if limit:
        scan_kwargs["Limit"] = limit
    if exclusive_start_key:
        scan_kwargs["ExclusiveStartKey"] = exclusive_start_key

    response = ddb_client.scan(**scan_kwargs)
    deserializer = TypeDeserializer()
    videos = [
        {k: deserializer.deserialize(v) for k, v in item.items()}
        for item in response.get("Items", [])
        if sort_key in item
    ]
    
    videos.sort(
        key=lambda x: x.get(sort_key),
        reverse=(sort_order.lower() == "desc")
    )
    
    result = {"videos": videos}
    
    if "LastEvaluatedKey" in response:
        try:
            next_token = base64.b64encode(
                json.dumps(response["LastEvaluatedKey"]).encode('utf-8')
            ).decode('utf-8')
            result["nextToken"] = next_token
        except Exception as e:
            logger.error(f"Error encoding pagination token: {e}")
    
    return result