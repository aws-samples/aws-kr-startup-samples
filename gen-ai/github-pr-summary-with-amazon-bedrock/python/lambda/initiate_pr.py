import json
import logging
import os
import boto3
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def parse_github_event(event):
    logger.info(f'Event: {event}')
    return json.loads(event['body']) if isinstance(event['body'], str) else event['body']


def is_valid_pr_event(github_event):
    if 'pull_request' not in github_event:
        return False, 'Not a Pull Request event'
    if github_event['action'] not in ['opened', 'reopened']:
        return False, 'Event ignored - not a PR creation event'
    return True, ''


def get_pr_diff(diff_url):
    return requests.get(diff_url).text


def generate_bedrock_prompt(diff_content):
    system_prompt = """
    You are responsible for code review. Please analyze the given PR diff and proceed with the following process:

    (TL;DR) Based on the entire content, analyze the purpose of the PR and the main changes:
    - Summarize concisely in 3 or 4 bullet points.

    (Highlights) Identify notable key parts from the entire content and analyze the code changes:
    - List each major change as an individual bullet point, using sub-points to explain details if necessary.
    - Explain as clearly and concisely as possible, quoting code when necessary to illustrate your points.
    - When quoting code blocks, use either `code block` or ```code block``` format as appropriate to the situation.
    - When using ```code block``` format, ensure that you maintain the original indentation of the code. This is crucial for preserving the structure and readability of the code.


    Please provide the results in the following Markdown format:
    ## TL;DR
    - sentence#1
    - sentence#2

    ## Highlights
    - sentence#1
    - sentence#2
    - sub-sentence#1
    - sub-sentence#2
      ```code block```

    Important Rule: The final output must be written in Korean.
    """

    user_prompt = f"""
    The following text contains the diff content of a GitHub Pull Request. Please analyze these changes and provide a summary that includes:
    
    The overall purpose of the PR
    Key modifications and their impact
    Any notable additions or deletions
    Potential areas of concern or improvement

    Please structure your response according to the format specified in the system prompt.
    ---
    {diff_content}
    """

    return system_prompt, user_prompt


def invoke_bedrock(bedrock_client, model_id, system_prompt, user_prompt):
    body = json.dumps({
        "anthropic_version": "",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": 0.1,
        "top_p": 1,
        "system": system_prompt,
    })

    response = bedrock_client.invoke_model(body=body, modelId=model_id)
    response_body = json.loads(response['body'].read())
    return response_body['content'][0]['text']


def lambda_handler(event, context):
    github_event = parse_github_event(event)

    is_valid, error_message = is_valid_pr_event(github_event)
    if not is_valid:
        return {
            'statusCode': 400,
            'body': json.dumps(error_message)
        }

    github_token = os.environ['GITHUB_TOKEN']
    diff_url = github_event['pull_request']['diff_url']
    comments_url = github_event['pull_request']['comments_url']

    region = os.environ.get('REGION', 'us-east-1')
    model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
    bedrock_client = boto3.client('bedrock-runtime', region_name=region)

    diff_content = get_pr_diff(diff_url)
    system_prompt, user_prompt = generate_bedrock_prompt(diff_content)
    summary = invoke_bedrock(bedrock_client, model_id, system_prompt, user_prompt)

    return {
        'summary': summary,
        'comments_url': comments_url,
        'github_token': github_token
    }
