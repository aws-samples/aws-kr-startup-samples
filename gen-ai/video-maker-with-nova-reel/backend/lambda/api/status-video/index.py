import boto3
import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME = os.environ.get('VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

ddb_client = boto3.client('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def update_dynamo_status(invocation_id, new_status, s3_uri=None):
    """Function to update DynamoDB status"""
    update_expression = 'SET #status = :status, updated_at = :updated_at'
    expression_values = {
        ':status': {'S': new_status},
        ':updated_at': {'S': datetime.now().isoformat()}
    }
    
    if s3_uri:
        update_expression += ', s3_uri = :s3_uri'
        expression_values[':s3_uri'] = {'S': s3_uri}
    
    try:
        ddb_client.update_item(
            TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
            Key={
                'invocation_id': {'S': invocation_id},
                'created_at': {'S': created_at}
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues=expression_values
        )
        logger.info(f"Updated status to {new_status} for invocation {invocation_id}")
    except Exception as e:
        logger.error(f"Error updating DynamoDB for invocation {invocation_id}: {e}")
        raise

def lambda_handler(event, context):
    logger.info("Checking video generation status...")
    
    try:
        # Query items with InProgress status from DynamoDB
        response = ddb_client.scan(
            TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
            FilterExpression='#status = :status',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': {'S': 'InProgress'}
            }
        )
        
        items = response.get('Items', [])
        logger.info(f"Found {len(items)} items in progress")
        logger.info(f"Items: {json.dumps(items, indent=2)}")
        
        total_processed = 0
        
        for item in items:
            try:
                invocation_arn = item.get('invocation_arn', {}).get('S')
                invocation_id = item.get('invocation_id', {}).get('S')
                
                logger.info(f"Processing invocation_arn: {invocation_arn}")
                logger.info(f"Processing invocation_id: {invocation_id}")
                
                if not invocation_arn or not invocation_id:
                    continue
                    
                # Check Bedrock invoke status
                logger.info(f"Checking status with ARN: {invocation_arn}")
                status_response = bedrock_runtime.get_async_invoke(
                    invocationArn=invocation_arn
                )
                
                # Serialize response containing datetime objects to JSON
                logger.info(f"Status response: {json.dumps(status_response, default=json_serial, indent=2)}")
                
                current_status = status_response.get('status')
                logger.info(f"Status for invocation {invocation_id}: {current_status}")
                
                # Update DynamoDB when completed
                if current_status in ['Completed', 'Failed']:
                    new_status = 'Completed' if current_status == 'Completed' else 'Failed'
                    
                    # Extract S3 URI if status is Completed
                    s3_uri = None
                    if new_status == 'Completed' and 'outputDataConfig' in status_response:
                        s3_config = status_response['outputDataConfig'].get('s3OutputDataConfig', {})
                        s3_uri = s3_config.get('s3Uri')
                    
                    update_dynamo_status(invocation_id, new_status, s3_uri)
                    total_processed += 1
                
            except Exception as e:
                logger.error(f"Error checking status for invocation {invocation_id}: {e}")
                logger.error(f"Exception details: {str(e)}")
                continue
        
        logger.info(f"Total invocations processed: {total_processed}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Status check completed',
                'processed': total_processed
            })
        }
        
    except Exception as e:
        logger.error(f"Error in status check: {e}")
        raise