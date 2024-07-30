import boto3
import os
import json
from botocore.exceptions import ClientError

bedrock_agent = boto3.client('bedrock-agent')

def handler(event, context):
    knowledge_base_id = os.environ['KNOWLEDGE_BASE_ID']
    
    try:
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            description='Ingestion job started after stack deployment'
        )
        
        print(f"Ingestion job started successfully. Job ID: {response['ingestionJobId']}")
        return {
            'statusCode': 200,
            'body': json.dumps('Ingestion job started successfully')
        }
    except ClientError as e:
        print(f"Error starting ingestion job: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error starting ingestion job: {str(e)}')
        }