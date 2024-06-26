import json
import logging
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    summary = event['summary']
    comments_url = event['comments_url']
    github_token = event['github_token']

    # Create PR comment
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    data = {
        'body': summary
    }
    response = requests.post(comments_url, headers=headers, json=data)

    if response.status_code == 201:
        logger.info('Successfully created PR comment')
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully created PR summary information.')
        }
    else:
        logger.error(f'Failed to create PR comment. Status code: {response.status_code}, Response: {response.text}')
        return {
            'statusCode': 500,
            'body': json.dumps('Failed to create PR comment.')
        }
