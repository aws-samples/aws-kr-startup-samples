import json
import os
import boto3
import urllib3

MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# Initialize AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
bedrock_runtime_client = boto3.client('bedrock-runtime')
secretsmanager_client = boto3.client('secretsmanager')

# Set the Slack API URL and fetch the Slack token from Secrets Manager
SLACK_URL = 'https://slack.com/api/chat.postMessage'
slack_token = json.loads(
    secretsmanager_client.get_secret_value(
        SecretId=os.environ.get('token')
    )['SecretString']
)['token']

http = urllib3.PoolManager()

def retrieve_knowledge_base(question):
    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId="<KNOWLEDGE_BASE_ID>",
        retrievalQuery={
            'text': question
        }
    )
    
    retrieval_results = response.get('retrievalResults', [])
    
    if retrieval_results:
        first_result = retrieval_results[0]
        content = first_result.get('content', {}).get('text', '내용을 찾을 수 없습니다.')
        confluence_url = first_result.get('location', {}).get('confluenceLocation', {}).get('url', '')
        return content, confluence_url
    else:
        return "검색 결과가 없습니다.", ""

def call_bedrock(question):
    kb_result, confluence_url = retrieve_knowledge_base(question)
    
    messages = [
        {
            "role": "user",
            "content": f"""당신은 HR Assistant입니다. 사용자는 신규 입사자이며 회사 규정에 대한 질문을 주로 합니다. 질문에 대한 대답을 모르겠으면 모른다고 말하세요.
다음은 질문에 관련된 정보입니다:
{kb_result}
이 정보를 바탕으로 다음 질문에 답변해주세요: {question}"""
        }
    ]
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": messages
    })
    
    accept = 'application/json'
    content_type = 'application/json'
    
    response = bedrock_runtime_client.invoke_model(
        body=body,
        modelId=MODEL_ID,
        accept=accept,
        contentType=content_type
    )
    
    response_body = json.loads(response['body'].read())
    
    content = response_body.get('content', [])
    if content and isinstance(content, list) and len(content) > 0:
        answer = content[0].get('text', '')
    else:
        answer = "응답을 생성하는 데 문제가 발생했습니다."
    
    return answer, confluence_url

def send_slack_message(channel, user, message, confluence_url):
    if confluence_url:
        message += f"\n\n참조 링크: {confluence_url}"
    
    data = {
        'channel': channel,
        'text': f"<@{user}> {message}"
    }
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json',
    }
    http.request(
        'POST',
        SLACK_URL,
        headers=headers,
        body=json.dumps(data)
    )

def handler(event, context):
    slack_body = event
    slack_event = slack_body.get('event', {})
    slack_text = slack_event.get('text', '')
    slack_user = slack_event.get('user')
    channel = slack_event.get('channel')

    # Replace the bot username with an empty string
    msg, confluence_url = call_bedrock(slack_text.replace('<@U06D5B8AR8R>', ''))
    
    # Send the message to Slack with the Confluence URL
    send_slack_message(channel, slack_user, msg, confluence_url)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Processing completed')
    }