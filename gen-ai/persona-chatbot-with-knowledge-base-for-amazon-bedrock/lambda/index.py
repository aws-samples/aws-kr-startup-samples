import boto3
import os
import json

bedrock_agent = boto3.client('bedrock-agent')

def handler(event, context):
    knowledge_base_id = os.environ['KNOWLEDGE_BASE_ID']
    data_source_id = os.environ['DATA_SOURCE_ID']
    
    try:
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            description='Ingestion job started after stack deployment',
            dataSourceId=data_source_id
        )
        
        ingestion_job_id = response['ingestionJob']['ingestionJobId']
        print(f"Ingestion job started successfully. Job ID: {ingestion_job_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'ingestionJobId': ingestion_job_id})
        }
    except Exception as e:
        print(f"Error starting ingestion job: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }