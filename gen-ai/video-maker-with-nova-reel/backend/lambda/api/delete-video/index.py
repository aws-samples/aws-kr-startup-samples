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
s3_client = boto3.client('s3')

def create_response(status_code, body):
    """
    Unified function for generating HTTP responses.
    """
    return {
        'statusCode': status_code,
        'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods': 'GET,OPTIONS,POST,DELETE'
            },
        'body': json.dumps(body)
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
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS,POST,DELETE'
            },
            'body': json.dumps({})
        }
    
    if http_method != 'DELETE':
        return create_response(405, {'error': f"{http_method} Methods are not allowed."})
    
    # URL 경로에서 invocation_id 추출
    path_parameters = event.get('pathParameters', {})
    if not path_parameters or 'invocation_id' not in path_parameters:
        return create_response(400, {'error': 'invocation_id is required in path parameters'})
    
    invocation_id = path_parameters['invocation_id']
    
    try:
        deleted_items = []
        failed_items = []
        
        try:
            # 먼저 invocation_id로 항목을 쿼리하여 created_at 값을 얻습니다
            query_response = ddb_client.query(
                TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
                KeyConditionExpression='invocation_id = :invocation_id',
                ExpressionAttributeValues={
                    ':invocation_id': {'S': invocation_id}
                },
                Limit=1
            )
            
            items = query_response.get('Items', [])
            if not items:
                failed_items.append({
                    'invocation_id': invocation_id,
                    'reason': 'Item not found'
                })
            else:
                # created_at 값 가져오기
                created_at = items[0].get('created_at', {}).get('S')
                if not created_at:
                    failed_items.append({
                        'invocation_id': invocation_id,
                        'reason': 'created_at not found'
                    })
                else:
                    # 파티션 키와 정렬 키를 모두 포함하여 DynamoDB에서 해당 invocation_id로 아이템 조회
                    response = ddb_client.get_item(
                        TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
                        Key={
                            'invocation_id': {'S': invocation_id},
                            'created_at': {'S': created_at}
                        }
                    )
                    
                    # 아이템이 존재하지 않는 경우
                    if 'Item' not in response:
                        failed_items.append({
                            'invocation_id': invocation_id,
                            'reason': 'Item not found'
                        })
                    else:
                        # DynamoDB 응답을 파이썬 딕셔너리로 변환
                        deserializer = TypeDeserializer()
                        item = {k: deserializer.deserialize(v) for k, v in response['Item'].items()}
                        
                        # S3 객체 삭제
                        if 'location' in item:
                            s3_url = item['location']
                            if s3_url.startswith('s3://'):
                                # s3://bucket-name/key format
                                bucket = s3_url.split('/')[2]
                                key = '/'.join(s3_url.split('/')[3:])
                                # 파일 경로에서 디렉토리 경로 추출 (output.mp4 제거)
                                directory_key = '/'.join(key.split('/')[:-1]) if '/' in key else key
                            elif s3_url.startswith('http'):
                                # https://bucket-name.s3.region.amazonaws.com/key format
                                domain_parts = s3_url.split('/')[2].split('.')
                                bucket = domain_parts[0]
                                key = '/'.join(s3_url.split('/')[3:])
                                # 파일 경로에서 디렉토리 경로 추출 (output.mp4 제거)
                                directory_key = '/'.join(key.split('/')[:-1]) if '/' in key else key
                            else:
                                logger.warning(f"Unsupported S3 URL format: {s3_url}")
                                bucket = None
                                directory_key = None
                            
                            # S3에서 오브젝트 삭제 (지원되지 않는 URL 형식인 경우 건너뜀)
                            if bucket and directory_key:
                                # S3 리소스를 사용하여 디렉토리 내 모든 객체 삭제
                                logger.info(f"Deleting all objects in directory: bucket={bucket}, directory={directory_key}")
                                s3_resource = boto3.resource('s3')
                                bucket_resource = s3_resource.Bucket(bucket)
                                bucket_resource.objects.filter(Prefix=directory_key).delete()
                                logger.info(f"Successfully deleted all objects with prefix {directory_key}")
                        
                        # DynamoDB 아이템 삭제 (파티션 키와 정렬 키 모두 포함)
                        logger.info(f"Deleting DynamoDB item with invocation_id: {invocation_id}")
                        ddb_client.delete_item(
                            TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
                            Key={
                                'invocation_id': {'S': invocation_id},
                                'created_at': {'S': created_at}
                            }
                        )
                        
                        deleted_items.append(invocation_id)
                        
        except Exception as e:
            logger.error(f"Error deleting item {invocation_id}: {str(e)}")
            failed_items.append({
                'invocation_id': invocation_id,
                'reason': str(e)
            })
        
        result = {
            'deleted': deleted_items,
            'failed': failed_items
        }
        
        if failed_items:
            return create_response(404 if 'Item not found' in failed_items[0]['reason'] else 500, result)
        else:
            return create_response(200, result)
        
    except Exception as e:
        logger.error("Error deleting video: %s", e)
        return create_response(500, {'error': 'Internal server error'})
