import boto3
import os

def handler(event, context):
    codebuild = boto3.client('codebuild')
    
    gfpgan_project_name = os.environ['GFPGAN_PROJECT_NAME']
    
    # Start both builds in parallel
    gfpgan_response = codebuild.start_build(projectName=gfpgan_project_name)
    
    return {
        'GfpganBuildId': gfpgan_response['build']['id']
    }