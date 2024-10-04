import json
import boto3
import os

lambda_client = boto3.client('lambda')
LAMBDA2_FUNCTION_NAME = os.environ['LAMBDA2_FUNCTION_NAME']

def handle_challenge(event):
    """
    Handles the Slack challenge event for verifying the URL.
    """
    body = json.loads(event['body'])
    return {
        'statusCode': 200,
        'body': body['challenge']
    }

def invoke_lambda2_async(event_body):
    lambda_client.invoke(
        FunctionName=LAMBDA2_FUNCTION_NAME,
        InvocationType='Event',  # 비동기 호출
        Payload=json.dumps(event_body)
    )

def handler(event, context):
    event_body = json.loads(event.get("body"))
    
    if event_body.get("type") == "url_verification":
        return handle_challenge(event)
    
    # Lambda2를 비동기적으로 호출
    invoke_lambda2_async(event_body)
    
    # 즉시 200 응답 반환
    return {
        'statusCode': 200,
        'body': json.dumps({'message': "Request received and processing started"})
    }