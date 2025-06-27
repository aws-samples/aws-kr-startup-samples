import boto3
import json
import uuid
import os
from datetime import datetime
from typing import Dict, Any
import random

s3_client = boto3.client('s3')
ddb_client = boto3.client('dynamodb')
BUCKET_NAME = os.environ['BUCKET_NAME']
OBJECT_PATH = os.environ['OBJECT_PATH']
DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME = os.environ['DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME']
DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME = os.environ['DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME']

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

def generate_unique_id(user_id: str, style: str, gender: str) -> str:
    current_time = datetime.now().strftime("%Y%m%d%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{current_time}-{user_id}-{style}-{gender}-{unique_id}"

def generate_presigned_url(object_key: str) -> str:
    return s3_client.generate_presigned_url(
        'put_object',
        Params={'Bucket': BUCKET_NAME, 'Key': object_key, 'ContentType': 'image/jpeg'},
        ExpiresIn='300'
    )

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    if event['httpMethod'] == 'OPTIONS':
        return create_response(200, {})
    
    if event['httpMethod'] != 'POST':
        return create_response(405, {'error': f"{event['httpMethod']} Methods are not allowed."})
    
    try:
        # request body parse (if body is string, decode json)
        body = event.get('body')
        if body is None:
            return create_response(400, {'error': 'Bad Request: Body is required.'})
        
        # if body is json string, parse
        if isinstance(body, str):
            body = json.loads(body)
        
        user_id = body.get('userId')
        style = body.get('style')
        gender = body.get('gender')
        
        # required parameter check
        if not user_id or not style or not gender:
            return create_response(400, {'error': 'Bad Request: userId, style and gender values are required.'})
        
        # unique image name create
        image_id = generate_unique_id(user_id, style, gender)
        
        # # check style and gender is valid
        # ddb_response = ddb_client.query(
        #     TableName=DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME,
        #     KeyConditionExpression='#pk = :pk',
        #     FilterExpression='#g = :gender',
        #     ExpressionAttributeNames={
        #         '#pk': 'PK',
        #         '#g': 'gender'
        #     },
        #     ExpressionAttributeValues={
        #         ':pk': {'S': f'STYLE#{style}'},
        #         ':gender': {'S': gender}
        #     }
        # )
    
        # if not ddb_response['Items']:
        #     raise Exception(f"Could not find image with style({style}) and gender({gender})")
        
        # random_item = random.choice(ddb_response['Items'])
        
        # uuid and userId and theme info to ddb with proper DynamoDB types
        ddb_client.put_item(
            TableName=DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME,
            Item={
                'uuid': {'S': image_id},
                'userId': {'S': user_id},
                'style': {'S': style},
                'gender': {'S': gender},
                # 'image_path': {'S': random_item['image_path']['S']},
                # 'story_short': {'S': random_item['story_short']['S']},
                # 'story_short_en': {'S': random_item['story_short_en']['S']},
                # 'query': {'S': random_item['query']['S']},
                # 'theme': {'S': random_item['theme']['S']},
                'updated_at': {"S": datetime.now().isoformat()},
                'created_at': {"S": datetime.now().isoformat()}
            }
        )

        # userId and theme info to path (OBJECT_PATH is the default path on S3)
        object_key = f"{OBJECT_PATH}/{image_id}.jpeg"
        # presigned url generate
        presigned_url = generate_presigned_url(object_key)

        return create_response(200, {
            'uploadUrl': presigned_url,
            'uuid': image_id
        })

    except Exception as e:
        return create_response(500, {'error': f'Internal server error: {str(e)}'})