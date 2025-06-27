import boto3
import os

def handler(event, context):
    codebuild = boto3.client('codebuild')
    
    facechain_project_name = os.environ['FACECHAIN_PROJECT_NAME']
    
    # Start both builds in parallel
    facechain_response = codebuild.start_build(projectName=facechain_project_name)
    
    return {
        'FaceChainBuildId': facechain_response['build']['id']
    }