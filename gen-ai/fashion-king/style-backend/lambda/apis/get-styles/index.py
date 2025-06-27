import boto3
import os
import json
from typing import Dict, List

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DDB_GENERATIVE_STYLIST_FASHION_STYLE_TABLE_NAME'])

def lambda_handler(event, context) -> Dict:
    try:
        # Scan the entire table to get all styles
        response = table.scan()
        items = response['Items']
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'styles': items
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': str(e)
            })
        } 