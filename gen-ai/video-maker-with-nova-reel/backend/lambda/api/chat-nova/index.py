import boto3
import json
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables safely (add appropriate exception handling if needed)
MODEL_ID = os.environ.get('MODEL_ID')
AWS_REGION = 'us-east-1'  # Default region setting for Amazon Nova Pro

system = [
    {
        "text": """You are an AI Prompt Engineering Assistant specialized in creating and optimizing visual prompts following specific guidelines. Your purpose is to help users create effective prompts for image generation or improve existing ones.

Core Functions:
1. Generate new prompts or refine existing ones according to these key principles:
- Structure prompts as scene descriptions rather than commands
- Use semicolons (;) to separate details
- Include camera movements at the start or end
- Keep prompts within 512 characters
- Replace negative words with positive alternatives
- Incorporate recommended keywords: 4k, cinematic, high quality, detailed, realistic, slow motion, dolly zoom

2. When responding:
- First analyze the user's request or existing prompt
- Provide the optimized/new prompt
- Explain key changes or reasoning (if needed)
- Suggest variations or improvements

Standard Format:
Scene Description: [main scene elements]
Technical Qualities: [4k; cinematic; high quality, etc.]
Atmosphere: [lighting; mood; environment]
Camera Movement: [specific camera direction]

Example Output:
"Gentle waves washing over seashells on pristine beach; golden morning light; 4k; cinematic quality; hyper detailed; soft focus; camera slowly tracking forward"

Remember:
- Always maintain visual clarity and coherence
- Focus on positive descriptions
- Ensure technical feasibility
- Consider composition and timing
"""
    }
]
inf_params = {"maxTokens": 1000, "topP": 0.1, "temperature": 0.3}
additionalModelRequestFields = {
    "inferenceConfig": {
         "topK": 20
    }
}

def create_response(status_code, body):
    """
    Unified function for generating HTTP responses.
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
    If the body is a string, parse it as JSON; if it's already a dict, return it directly.
    Return None if a parsing error occurs.
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
        return create_response(405, {'error': f"{http_method} Methods are not allowed."})
        
    # Parse and validate the request body
    body = event.get('body')
    parsed_body = parse_body(body)
    if not parsed_body:
        return create_response(400, {'error': 'Bad Request: A valid body is required.'})
        
    logger.info("Received messages: %s", parsed_body)
    
    bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    

    try:
        response = bedrock_runtime.converse(
            modelId=MODEL_ID, 
            messages=parsed_body, 
            system=system, 
            inferenceConfig=inf_params,
            additionalModelRequestFields=additionalModelRequestFields
        )

        message = response["output"]["message"]["content"][0]["text"]

    except Exception as e:
        logger.error("Bedrock invocation error: %s", e)
        return create_response(500, {'error': 'Server error: Failed to generate response.'})

    return create_response(200, {
        'message': message
    })