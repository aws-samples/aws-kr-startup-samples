import json
import boto3
import os
import urllib.request
import urllib.error
import io
from datetime import datetime

DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME = os.environ['DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME']
DDB_GENERATIVE_STYLIST_IMAGE_DISPLAY_TABLE_NAME = os.environ['DDB_GENERATIVE_STYLIST_IMAGE_DISPLAY_TABLE_NAME']
DDB_KMS_KEY_ARN = os.environ['DDB_KMS_KEY_ARN']

ddb_client = boto3.client('dynamodb')

def lambda_handler(event, context):
    # S3 이벤트 처리
    s3_event = event['Records'][0]['s3']
    encoded_object_key = s3_event['object']['key']
    result_object_key = urllib.parse.unquote_plus(encoded_object_key) # user's result image
    result_object_filename = os.path.basename(result_object_key) # result_object_filename: {current_time}-{user_id}-{style}-{gender}-{unique_id}.jpeg
    uuid = os.path.splitext(result_object_filename)[0]
    userId = uuid.split('-')[1]
    style = uuid.split('-')[2]
    gender = uuid.split('-')[3]

    print("uuid:", uuid)
    print("userId:", userId)
    print("style:", style)
    print("gender:", gender)

    # get process image info
    ddb_response = ddb_client.query(
        TableName=DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME,
        KeyConditionExpression='#uuid = :uuid',
        ExpressionAttributeNames={
            '#uuid': 'uuid'
        },
        ExpressionAttributeValues={
            ':uuid': {'S': uuid}
        }
    )
    
    if not ddb_response['Items']:
        raise Exception(f"Could not find image with uuid({uuid})")

    process_image_info = ddb_response['Items'][0]
    image_path = process_image_info['image_path']['S']
    story_short = process_image_info['story_short']['S']
    story_short_en = process_image_info['story_short_en']['S']
    query = process_image_info['query']['S']
    theme = process_image_info['theme']['S']
    
    # userId로 기존 아이템 조회
    try:
        response = ddb_client.query(
            TableName=DDB_GENERATIVE_STYLIST_IMAGE_DISPLAY_TABLE_NAME,
            KeyConditionExpression='userId = :userId',
            ExpressionAttributeValues={
                ':userId': {'S': userId}
            }
        )
        
        current_time = datetime.now().isoformat()
        
        if response['Items']:
            # 기존 아이템이 있는 경우 업데이트
            ddb_client.update_item(
                TableName=DDB_GENERATIVE_STYLIST_IMAGE_DISPLAY_TABLE_NAME,
                Key={
                    'userId': {'S': userId}
                },
                UpdateExpression='SET #uuid_attr = :uuid, image_path = :image_path, story_short = :story_short, story_short_en = :story_short_en, #query_attr = :query, theme = :theme, updated_at = :updated_at, #style_attr = :style, gender = :gender',
                ExpressionAttributeNames={
                    '#uuid_attr': 'uuid',
                    '#query_attr': 'query',
                    '#style_attr': 'style'
                },
                ExpressionAttributeValues={
                    ':uuid': {'S': uuid},
                    ':image_path': {'S': image_path},
                    ':story_short': {'S': story_short},
                    ':story_short_en': {'S': story_short_en},
                    ':query': {'S': query},
                    ':theme': {'S': theme},
                    ':updated_at': {'S': current_time},
                    ':style': {'S': style},
                    ':gender': {'S': gender}
                }
            )
        else:
            # 새로운 아이템 생성
            ddb_client.put_item(
                TableName=DDB_GENERATIVE_STYLIST_IMAGE_DISPLAY_TABLE_NAME,
                Item={
                    'uuid': {'S': uuid},
                    'userId': {'S': userId},
                    'style': {'S': style},
                    'gender': {'S': gender},
                    'image_path': {'S': image_path},
                    'story_short': {'S': story_short},
                    'story_short_en': {'S': story_short_en},
                    'query': {'S': query},
                    'theme': {'S': theme},
                    'updated_at': {'S': current_time},
                    'created_at': {'S': current_time}
                }
            )
    except Exception as e:
        print(f"DynamoDB 작업 중 오류 발생: {str(e)}")
        raise e
    
    return {
        'statusCode': 200,
        'body': json.dumps('Face swap complete')
    }
