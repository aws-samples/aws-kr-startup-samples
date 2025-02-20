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
    
    # 쿼리 스트링으로 pagination 파라미터(limit, nextToken) 추출
    query_params = event.get("queryStringParameters") or {}
    logger.info("Query params: %s", query_params)
    
    limit = None
    if "limit" in query_params:
        try:
            limit = int(query_params.get("limit"))
        except ValueError as e:
            logger.error("유효하지 않은 limit 값: %s", query_params.get("limit"))
    
    exclusive_start_key = None
    if "nextToken" in query_params and query_params.get("nextToken"):
        next_token_str = query_params.get("nextToken")
        try:
            # nextToken은 base64 인코딩 된 JSON 문자열이므로 디코딩 후 dict로 변환
            exclusive_start_key = json.loads(base64.b64decode(next_token_str).decode('utf-8'))
        except Exception as e:
            logger.error("유효하지 않은 nextToken 값: %s", next_token_str)
    
    data = list_videos(limit, exclusive_start_key)
    logger.info("List videos data: %s", data)
    # data는 {"videos": [...], "nextToken": "..."} 구조로 반환
    return create_response(200, data)

def list_videos(limit=None, exclusive_start_key=None):
    """
    DynamoDB의 VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME 테이블에서 항목을 조회하여
    리스트와 (있다면) pagination 토큰(nextToken)을 반환합니다.
    """
    scan_kwargs = {
        "TableName": VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME
    }
    if limit:
        scan_kwargs["Limit"] = limit
    if exclusive_start_key:
        scan_kwargs["ExclusiveStartKey"] = exclusive_start_key

    try:
        response = ddb_client.scan(**scan_kwargs)
    except Exception as e:
        logger.error("DynamoDB 스캔 중 오류 발생: %s", e)
        return {"videos": []}
    
    items = response.get("Items", [])
    deserializer = TypeDeserializer()
    
    def deserialize_item(item):
        return {key: deserializer.deserialize(value) for key, value in item.items()}
    
    videos = [deserialize_item(item) for item in items]
    result = {"videos": videos}
    
    # 결과에 LastEvaluatedKey가 있다면 다음 페이지가 있으므로 nextToken 생성
    if "LastEvaluatedKey" in response:
        try:
            # DynamoDB에서 반환된 LastEvaluatedKey는 JSON 직렬화가 어려울 수 있으므로 base64 인코딩 처리
            next_token = base64.b64encode(json.dumps(response["LastEvaluatedKey"]).encode('utf-8')).decode('utf-8')
            result["nextToken"] = next_token
        except Exception as e:
            logger.error("토큰 인코딩 오류: %s", e)
    
    return result