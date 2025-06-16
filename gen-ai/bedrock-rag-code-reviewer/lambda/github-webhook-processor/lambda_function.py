import json
import os
import boto3
import hashlib
import hmac

# === CONFIG ===
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")
GIT_PUSH_ANALYZER_FUNCTION_NAME = os.environ.get("GIT_PUSH_ANALYZER_FUNCTION_NAME")
REGION = os.environ.get("AWS_REGION")

# Initialize AWS clients
lambda_client = boto3.client("lambda", region_name=REGION)

def lambda_handler(event, context):
    """Main Lambda handler for GitHub push webhooks - processes webhook and delegates to analyzer"""
    
    # Verify GitHub webhook signature
    if not verify_github_signature(event):
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'Unauthorized - GitHub webhook signature required'})
        }
    
    # Parse the webhook payload
    try:
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON payload'})
        }
    
    # Check if this is a push event to main/master branch
    if not is_main_branch_push_event(body):
        print("Not a main branch push event, skipping")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Not a main branch push event'})
        }
    
    try:
        # Extract basic push information
        push_info = extract_push_info(body)
        print(f"Processing push: {push_info['commits_count']} commits to {push_info['branch']}")
        
        # Invoke the git-push-analyzer Lambda function asynchronously
        response = lambda_client.invoke(
            FunctionName=GIT_PUSH_ANALYZER_FUNCTION_NAME,
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps({
                'push_info': push_info,
                'webhook_payload': body
            })
        )
        
        print(f"Successfully invoked git-push-analyzer: {response['StatusCode']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Push webhook received and analyzer invoked',
                'commits_count': push_info['commits_count'],
                'branch': push_info['branch'],
                'head_sha': push_info['head_sha'][:8]
            })
        }
        
    except Exception as e:
        import traceback
        print(f"Error processing webhook: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def verify_github_signature(event):
    """Verify GitHub webhook signature"""
    if not GITHUB_WEBHOOK_SECRET:
        print("WARNING: GitHub webhook secret not configured")
        return True  # Skip verification if secret not set
    
    headers = event.get('headers') or {}
    signature = headers.get('x-hub-signature-256', '') or headers.get('X-Hub-Signature-256', '')
    
    if not signature:
        print("ERROR: No GitHub signature found in headers - only GitHub webhooks are supported")
        return False
    
    body = event.get('body', '')
    
    # Ensure body is bytes
    if isinstance(body, str):
        body = body.encode('utf-8')
    elif body is None:
        body = b''
    elif not isinstance(body, (bytes, bytearray)):
        body = str(body).encode('utf-8')
    
    expected_signature = 'sha256=' + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

def is_main_branch_push_event(payload):
    """Check if the webhook event is a push to main/master branch"""
    return (
        payload.get('ref') == 'refs/heads/main' or
        payload.get('ref') == 'refs/heads/master'
    )

def extract_push_info(payload):
    """Extract relevant information from push webhook payload"""
    return {
        'commits_count': len(payload['commits']),
        'branch': payload['ref'].split('/')[-1],
        'head_sha': payload['head_commit']['id'],
        'before_sha': payload['before'],
        'after_sha': payload['after'],
        'repo_full_name': payload['repository']['full_name'],
        'repo_clone_url': payload['repository']['clone_url'],
        'pushed_at': payload['head_commit']['timestamp'],
        'pusher': payload['pusher']['name'],
        'commits': payload['commits']
    } 