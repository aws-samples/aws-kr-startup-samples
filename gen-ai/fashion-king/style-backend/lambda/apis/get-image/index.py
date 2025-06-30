import boto3
import json
import uuid
import os
from datetime import datetime
from typing import Dict, Any

s3_client = boto3.client('s3')
ddb_client = boto3.client('dynamodb')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
DDB_GENERATIVE_STYLIST_IMAGE_DISPLAY_TABLE_NAME = os.environ.get('DDB_GENERATIVE_STYLIST_IMAGE_DISPLAY_TABLE_NAME')
DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME = os.environ.get('DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME')
def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status_code,
        'body': json.dumps(body),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
        }
    }

def generate_presigned_url(object_key: str) -> str:
    return s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': object_key,
            'ResponseContentType': 'image/jpeg'
        },
        ExpiresIn='300'
    )

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    if event['httpMethod'] == 'OPTIONS':
        return create_response(200, {})
    
    if event['httpMethod'] != 'GET':
        return create_response(405, {'error': f"{event['httpMethod']} Methods are not allowed."})
    
    try:
        # path parameter에서 userId 가져오기
        path_parameters = event.get('pathParameters', {})
        user_id = path_parameters.get('userId')

        if not user_id:
            return create_response(400, {'error': 'Bad Request: userId is required.'})
        
        # DynamoDB에서 user_id에 해당하는 아이템 조회
        response = ddb_client.get_item(
            TableName=DDB_GENERATIVE_STYLIST_IMAGE_DISPLAY_TABLE_NAME,
            Key={
                'userId': {'S': user_id}
            }
        )
        
        # 조회된 아이템이 있는지 확인
        item = response.get('Item')
        if not item:
            return create_response(404, {'error': 'User not found'})

        uuid = item.get('uuid', {}).get('S')
        image_path = item.get('image_path', {}).get('S')
        story_short = item.get('story_short', {}).get('S')
        story_short_en = item.get('story_short_en', {}).get('S')
        query = item.get('query', {}).get('S')
        theme = item.get('theme', {}).get('S')
        style = item.get('style', {}).get('S')
        gender = item.get('gender', {}).get('S')
        presigned_url = generate_presigned_url(image_path)

        return create_response(200, {
            'imageUrl': presigned_url,
            'storyShort': story_short,
            'storyShortEn': story_short_en,
            'query': query,
            'theme': theme,
            'style': style,
            'gender': gender,
            'uuid': uuid,
            'userId': user_id
        })

    except Exception as e:
        return create_response(500, {'error': f'Internal server error: {str(e)}'})