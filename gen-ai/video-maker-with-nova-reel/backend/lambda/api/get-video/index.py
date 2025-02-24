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
        'body': json.dumps(body),
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
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
    
    if http_method != 'GET':
        return create_response(405, {'error': f"{http_method} Methods are not allowed."})
    
    # path parameter에서 invocation_id 추출
    path_parameters = event.get('pathParameters', {})
    invocation_id = path_parameters.get('invocation_id')
    
    if not invocation_id:
        return create_response(400, {'error': 'invocation_id is required'})
    
    try:
        # DynamoDB에서 해당 invocation_id로 아이템 조회
        response = ddb_client.get_item(
            TableName=VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME,
            Key={'invocation_id': {'S': invocation_id}}
        )
        
        # 아이템이 존재하지 않는 경우
        if 'Item' not in response:
            return create_response(404, {'error': 'Video not found'})
        
        # DynamoDB 응답을 파이썬 딕셔너리로 변환
        deserializer = TypeDeserializer()
        item = {k: deserializer.deserialize(v) for k, v in response['Item'].items()}
        
        # location에서 S3 버킷과 키 추출
        if 'location' in item:
            s3_url = item['location']
            # s3://bucket-name/key 형식에서 버킷과 키 추출
            bucket = s3_url.split('/')[2]
            key = '/'.join(s3_url.split('/')[3:])

            print(s3_url)
            print(bucket)
            print(key)
            
            # presigned URL 생성 (5분 = 300초)
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=300
            )
            
            # 응답에 presigned URL 추가
            item['presigned_url'] = presigned_url
        
        return create_response(200, item)
        
    except Exception as e:
        logger.error("Error fetching video: %s", e)
        return create_response(500, {'error': 'Internal server error'})
