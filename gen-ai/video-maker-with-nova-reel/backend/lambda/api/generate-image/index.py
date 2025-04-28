import base64
import io
import json
import logging
import random
import uuid
import os
import time
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# S3 버킷 이름 환경 변수에서 가져오기
BUCKET_NAME = os.environ.get('BUCKET_NAME')
if not BUCKET_NAME:
    raise ValueError("BUCKET_NAME environment variable is required")

def generate_presigned_url(bucket, key, expiration=3600):
    """
    Generate a presigned URL for the S3 object
    """
    s3_client = boto3.client('s3')
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': key
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        raise

def upload_to_s3(image_bytes, key):
    """
    Upload image to S3 bucket
    """
    s3_client = boto3.client('s3')
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=image_bytes,
            ContentType='image/png'
        )
        return generate_presigned_url(BUCKET_NAME, key)
    except ClientError as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise

def generate_image(model_id, body):
    """
    Generate an image using Amazon Nova Canvas model on demand.
    """
    logger.info("Generating image with Amazon Nova Canvas model %s", model_id)

    bedrock = boto3.client(
        service_name='bedrock-runtime',
        config=Config(read_timeout=300)
    )

    accept = "application/json"
    content_type = "application/json"

    try:
        response = bedrock.invoke_model(
            body=body, 
            modelId=model_id, 
            accept=accept, 
            contentType=content_type
        )
        response_body = json.loads(response.get("body").read())

        if "error" in response_body and response_body["error"]:
            raise Exception(f"Image generation error: {response_body['error']}")

        image_urls = []
        timestamp = int(time.time())
        
        for idx, base64_image in enumerate(response_body.get("images", [])):
            # Base64 디코딩
            base64_bytes = base64_image.encode('ascii')
            image_bytes = base64.b64decode(base64_bytes)
            
            # S3에 업로드할 키 생성
            file_id = str(uuid.uuid4())
            key = f"generated-images/{file_id}.png"
            
            # S3에 업로드하고 presigned URL 받기
            presigned_url = upload_to_s3(image_bytes, key)
            image_urls.append({
                'url': presigned_url,
                'key': key
            })

        return image_urls

    except ClientError as e:
        logger.error(f"Bedrock client error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise

def handler(event, context):
    """
    Lambda function handler for generating images using Nova Canvas.
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract parameters
        prompt = body.get('prompt')
        negative_prompt = body.get('negative_prompt', '')
        height = int(body.get('height', 720))
        width = int(body.get('width', 1280))
        number_of_images = int(body.get('number_of_images', 1))

        if not prompt:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Prompt is required'})
            }

        # Prepare request body for Nova Canvas
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
            },
            "imageGenerationConfig": {
                "numberOfImages": number_of_images,
                "height": height,
                "width": width,
                "cfgScale": 8.0,
                "seed": random.randint(0, 858993459)
            }
        }

        # negative_prompt가 있는 경우에만 추가
        if negative_prompt and len(negative_prompt.strip()) > 0:
            request_body["textToImageParams"]["negativeText"] = negative_prompt

        # Generate images
        model_id = 'amazon.nova-canvas-v1:0'
        images = generate_image(
            model_id=model_id,
            body=json.dumps(request_body)
        )

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'images': images,
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'height': height,
                'width': width,
                'number_of_images': number_of_images
            })
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }

def handle_options(event, context):
    """
    Handle OPTIONS request for CORS
    """
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps({})
    } 