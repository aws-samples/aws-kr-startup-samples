import boto3
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
CLAUDE_MODEL_ID = os.environ.get('CLAUDE_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
AWS_REGION = 'us-east-1'  # Bedrock service region

# System prompt for storyboard creation
SYSTEM_PROMPT = """You are a video storyboard generation expert.
You need to create a 5-step storyboard that matches the user's input topic.
Each step should be written in the following format for use in video production:

1. Description: Detailed explanation of the scene content
2. Prompt: Video generation prompt for Nova Reel model (written in English, separated by semicolons)

The response must be in the following JSON format:
```json
{
  "title": "Storyboard Title",
  "scenes": [
    {
      "description": "Description of scene 1 (in Korean)",
      "prompt": "Scene 1 video generation prompt (in English, separated by semicolons)"
    },
    {
      "description": "Description of scene 2 (in Korean)",
      "prompt": "Scene 2 video generation prompt (in English, separated by semicolons)"
    },
    ...total of 5 scenes
  ]
}
```

Prompt writing rules:
1. Write scenes as descriptive statements, not commands (e.g., "ocean scenery" O, "show the ocean" X)
2. Separate details with semicolons (;)
3. Place camera movements at the beginning or end of the prompt
4. Keep each prompt within 512 characters
5. Avoid negative words such as "no", "without", "not doing"
6. Recommended keywords: 4k, cinematic, high quality, detailed, realistic, slow motion, dolly zoom, etc.

Example prompts:
"Slow cam of a man middle age; 4k; Cinematic; in a sunny day; peaceful; highest quality; dolly in;"
"Closeup of a large seashell in the sand. Gentle waves flow around the shell. Camera zoom in."

The response must strictly follow the above JSON format and should be a complete storyboard with 5 scenes that have logical connections and story flow that matches the topic."""

def create_response(status_code, body):
    """
    Integrated HTTP response generation function
    """
    return {
        'statusCode': status_code,
        'body': json.dumps(body),
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        }
    }

def parse_body(body):
    """
    Parse as JSON if it's a string, return as is if it's already a dict
    Return None if parsing error occurs
    """
    if not body:
        return None
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            logger.error("JSON parsing error: %s", e)
            return None
    return body

def lambda_handler(event, context):
    logger.info("Received event: %s", event)
    http_method = event.get('httpMethod', '')
    
    if http_method == 'OPTIONS':
        return create_response(200, {})
    
    if http_method != 'POST':
        return create_response(405, {'error': f"{http_method} method is not allowed."})
        
    # Parse and validate request body
    body = event.get('body')
    parsed_body = parse_body(body)
    if not parsed_body:
        return create_response(400, {'error': 'Invalid request: Valid body is required.'})
        
    topic = parsed_body.get('topic')
    if not topic:
        return create_response(400, {'error': 'Invalid request: topic field is required.'})
    
    bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    
    try:
        # Call Claude model
        response = bedrock_runtime.invoke_model(
            modelId=CLAUDE_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Topic: {topic}\n\nPlease create a 5-step storyboard that matches this topic."
                            }
                        ]
                    }
                ]
            }),
            contentType="application/json",
            accept="application/json"
        )
        
        response_body = json.loads(response.get('body').read())
        storyboard_text = response_body.get('content')[0].get('text')
        
        # Extract JSON response
        start_idx = storyboard_text.find('{')
        end_idx = storyboard_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            return create_response(500, {'error': 'Cannot extract JSON from Claude response.'})
        
        storyboard_json = json.loads(storyboard_text[start_idx:end_idx])
        
    except Exception as e:
        logger.error("Bedrock call error: %s", e)
        return create_response(500, {'error': f'Server error: Failed to generate storyboard. {str(e)}'})
    
    return create_response(200, {
        'message': 'Storyboard has been successfully generated.',
        'storyboard': storyboard_json
    })