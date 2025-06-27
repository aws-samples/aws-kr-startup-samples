import boto3
import json
import os
import copy
import urllib.parse
from io import BytesIO
from PIL import Image
from datetime import datetime
from typing import Dict, Any

s3_client = boto3.client('s3')
rekognition_client = boto3.client('rekognition')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
FACE_CROPPED_OBJECT_PATH = os.environ.get('FACE_CROPPED_OBJECT_PATH')
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

def lambda_handler(event, context):
    # S3 이벤트 처리
    s3_event = event['Records'][0]['s3']
    bucket_name = s3_event['bucket']['name']
    encoded_object_key = s3_event['object']['key']
    source_object_key = urllib.parse.unquote_plus(encoded_object_key)
    
    # Load image file from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=source_object_key)
    image_content = response['Body'].read()  
    image = Image.open(BytesIO(image_content))
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    
    # Detect faces and find the largest face area (with padding)
    ori_image, imgWidth, imgHeight, f_left, f_top, f_width, f_height, rekognition_response = show_faces(image, bucket_name, source_object_key)
    
    if f_left is not None:
        # Crop the detected face area
        cropped_image = ori_image.crop((f_left, f_top, f_left + f_width, f_top + f_height))
        
        # Extract the filename from source_object_key
        filename = os.path.basename(source_object_key)
        
        # Create the key for the cropped image
        face_cropped_object_key = os.path.join(FACE_CROPPED_OBJECT_PATH, filename)
        
        # Save the cropped image to a memory buffer in jpeg format and upload to S3
        buffered = BytesIO()
        cropped_image.save(buffered, format="JPEG")
        image_bytes = buffered.getvalue()
        s3_client.put_object(
            Bucket=bucket_name,
            Key=face_cropped_object_key,
            Body=image_bytes,
            ContentType="image/jpeg"
        )
        
        # Delete the original image from S3
        s3_client.delete_object(Bucket=bucket_name, Key=source_object_key)
        
        return {
            'statusCode': 200,
            'body': json.dumps(f"Cropped face image saved successfully at {face_cropped_object_key} and original image deleted.")
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps("No faces detected in the image.")
        }

def show_faces(image, bucket_name, object_key, padding_ratio=0.5):
    imgWidth, imgHeight = image.size
    ori_image = copy.deepcopy(image)
    
    # Save image to a memory buffer in jpeg format
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    image_bytes = buffer.getvalue()
    
    # If the image size exceeds MAX_IMAGE_SIZE, use S3 object reference for face detection
    if len(image_bytes) > MAX_IMAGE_SIZE:
        print(f"Image size exceeds {MAX_IMAGE_SIZE} bytes. Using S3 object reference.")
        response = rekognition_client.detect_faces(
            Image={'S3Object': {'Bucket': bucket_name, 'Name': object_key}},
            Attributes=['ALL']
        )
    else:
        response = rekognition_client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )
        
    largest_area = 0
    largest_face_box = None
    
    # Select the largest face area from each face area
    for faceDetail in response['FaceDetails']:
        box = faceDetail['BoundingBox']
        left = imgWidth * box['Left']
        top = imgHeight * box['Top']
        width = imgWidth * box['Width']
        height = imgHeight * box['Height']
        
        current_area = width * height
        if current_area > largest_area:
            largest_area = current_area
            largest_face_box = (left, top, width, height)
    
    if largest_face_box:
        left, top, width, height = largest_face_box
        # Apply padding (additional space)
        padding_width = width * padding_ratio
        padding_height = height * padding_ratio
        padded_left = max(0, left - padding_width)
        padded_top = max(0, top - padding_height)
        padded_right = min(imgWidth, left + width + padding_width)
        padded_bottom = min(imgHeight, top + height + padding_height)
        
        return ori_image, imgWidth, imgHeight, int(padded_left), int(padded_top), int(padded_right - padded_left), int(padded_bottom - padded_top), response
    else:
        return None, None, None, None, None, None, None, None
