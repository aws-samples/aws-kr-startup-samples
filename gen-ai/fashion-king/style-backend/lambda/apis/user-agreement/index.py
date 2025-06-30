import json
import boto3
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key

# DynamoDB 클라이언트 초기화
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DDB_AMAZON_BEDROCK_USER_AGREEMENT_TABLE_NAME'])

def handler(event, context):
    try:
        request_body = json.loads(event['body'])
        
        image_id = request_body.get('id')
        name = request_body.get('name')
        agree = request_body.get('agree')
        saved_at = request_body.get('savedAt')
        user_id = request_body.get('userId')

        print(f"image_id: {image_id}, name: {name}, agree: {agree}, saved_at: {saved_at}, user_id: {user_id}")
        
        if not image_id or not name or agree is None or not saved_at:
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Missing required fields'})
            }
        
        params = {
            'PK': f'USERID#{user_id}#NAME#{name}',
            'savedAt': saved_at,
            'name': name,
            'agree': agree,
            'userId': user_id,
            'imageId': image_id
        }
        
        response = table.put_item(Item=params)
      
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, Content-Length, X-Requested-With'
            },
            'body': json.dumps({'message': 'Item updated successfully'})
        }
    
    except Exception as e:
        print(f'Error: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal server error'})
        }