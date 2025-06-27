import base64
import datetime
import json
import boto3
import os
import urllib.parse
import random
import time

ddb_client = boto3.client('dynamodb')
sagemaker_runtime = boto3.client('sagemaker-runtime')
s3_client = boto3.client('s3')

BUCKET_NAME = os.environ['BUCKET_NAME']
RESULT_OBJECT_PATH = os.environ['RESULT_OBJECT_PATH']
SAGEMAKER_FACECHAIN_ENDPOINT_NAME = os.environ['SAGEMAKER_FACECHAIN_ENDPOINT_NAME']
DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME = os.environ['DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME']
DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME = os.environ['DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME']
COUNTRY = os.environ['COUNTRY']

bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-west-2')

def analyze_outfit(base64_image):

    # Prepare the request
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": """Analyze this image and provide a JSON response containing an Amazon search query URL that can be used to search for the top, bottom, and shoes on Amazon.com. The search query should include specific details such as the color, style (e.g., casual, formal, sporty, vintage), material (e.g., cotton, leather, denim), and notable design elements (e.g., patterns, prints, embellishments) of each item. Additionally, determine the appropriate gender category (men's, women's, unisex, etc.) based on the image and reflect it in the search query. Ensure that the JSON response follows the format below. \n\n{
                          "top": "https://www.amazon.in/s?k=white+crop+hoodie+sweatshirt",
                          "bottom": "https://www.amazon.in/s?k=white+jogger+pants",
                          "shoes": "https://www.amazon.in/s?k=white+running+shoes"
                        }"""
                    }
                ]
            }
        ]
    }

    # Invoke the model
    response = bedrock.invoke_model(
        body=json.dumps(request_body),
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        accept='application/json',
        contentType='application/json'
    )

    # Parse and return the response
    response_body = json.loads(response['body'].read())
    result = response_body['content'][0]['text']
    print(result)
    return result

def lambda_handler(event, context):
    s3_event = event['Records'][0]['s3']
    bucket_name = s3_event['bucket']['name']
    encoded_object_key = s3_event['object']['key']
    source_object_key = urllib.parse.unquote_plus(encoded_object_key) # user's cropped face image
    source_object_filename = os.path.basename(source_object_key) # source_object_filename: {current_time}-{user_id}-{style}-{gender}-{unique_id}.jpeg
    uuid = os.path.splitext(source_object_filename)[0] 
    style = uuid.split('-')[2]
    gender = uuid.split('-')[3]
    user_id = uuid.split('-')[1]  # userId 추출

    print(f"source_object_key: {source_object_key}")
    print(f"uuid: {uuid}")
    print(f"style: {style}")
    print(f"gender: {gender}")
    print(f"user_id: {user_id}")

    # ddb_response = ddb_client.query(
    #     TableName=DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME,
    #     KeyConditionExpression='#uuid = :uuid',
    #     ExpressionAttributeNames={
    #         '#uuid': 'uuid'
    #     },
    #     ExpressionAttributeValues={
    #         ':uuid': {'S': uuid}
    #     }
    # )
    
    # if not ddb_response['Items']:
    #     raise Exception(f"Could not find image with uuid({uuid})")
    
    # target_object_key = ddb_response['Items'][0]['image_path']['S']

    output_object_key = f"{RESULT_OBJECT_PATH}/{source_object_filename}"
   
    print(f"output_object_key: {output_object_key}")

    # Call Claude Multimodal to get face description
    # Get the image from S3 first
    image_obj = s3_client.get_object(Bucket=bucket_name, Key=source_object_key)
    image_data = image_obj['Body'].read()
    
    # Call Claude Multimodal endpoint using boto3
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        contentType='application/json',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64.b64encode(image_data).decode('utf-8')
                            }
                        },
                        {
                            "type": "text",
                            "text": """Describe the given virtual human's face in the image and provide a structured description (within 150 characters) including:
1. Age: [infant(0-2)/toddler(3-5)/child(6-12)/teen(13-19)/young adult(20-35)/adult(36-50)/middle-aged(51-65)/senior(66+)]
2. Demographics: [male/female/non-binary, korean/japanese/chinese/vietnamese/thai/indian/pakistani/iranian/turkish/russian/german/french/italian/spanish/british/american/canadian/mexican/brazilian/argentinian/egyptian/nigerian/south african/australian/mixed]
3. Face Shape: [oval/round/square/heart/diamond/rectangular/triangular]
4. Facial Fullness: [very slim/slim/slightly slim/average/slightly chubby/chubby/obese]
5. Face Ratio: [long/medium/wide, oval/round/square]
6. Hairstyle: [short/medium/long, straight/wavy/curly/coily, bald/balding, bangs/no bangs, layered/one-length, side-parted/middle-parted/undivided, slicked-back/loose, updo/down, fringe/undercut/pixie/bob/lob, with/without hair accessories]
7. Hair Color: [black/brown/blonde/red/gray/white/platinum/silver/brunette/auburn/chestnut/copper/golden/strawberry blonde/ash blonde/dark brown/light brown/salt and pepper/peppered gray/partially gray, bald/balding]
8. Facial Hair: [clean-shaven/stubble/short beard/medium beard/long beard/goatee/mustache/sideburns/mixed]
9. Eyebrows: [thin/medium/thick, straight/arched/curved, short/medium/long, sparse/dense, light/dark, high/low, close-set/wide-set, symmetrical/asymmetrical, sparse/medium/dense]
10. Jawline: [very sharp/sharp/soft/very soft, defined/undefined, angular/round, square/pointed, prominent/recessed, symmetrical/asymmetrical]
11. Cheekbones: [very high/high/moderate/low/very low, prominent/average/flat]
12. Skin Tone: [very fair/fair/medium/olive/tan/dark/very dark]
13. Eyes: [small/medium/large, round/almond/upturned/downturned, single/double/hooded/monolid, deep-set/protruding, close-set/wide-set, symmetrical/asymmetrical]
14. Nose: [small/medium/large, straight/curved/upturned/downturned, narrow/medium/wide]
15. Lips: [thin/medium/full, straight/curved, small/medium/large]
16. Forehead: [very high/high/average/low/very low, wide/narrow]



Format the response as a concise bullet-point list."""
                        }
                    ]
                }
            ]
        })
    )

    response_body = json.loads(response['body'].read())
    face_description = response_body['content'][0]['text']
    print(f"face_description: {face_description}")

    # Get style prompt from DynamoDB style table
    try:
        # First try to get style with specific country
        style_response = ddb_client.query(
            TableName=DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME,
            IndexName="CountryIndex",
            KeyConditionExpression='#country = :country',
            FilterExpression='#styleName = :style',
            ExpressionAttributeNames={
                '#country': 'Country',
                '#styleName': 'StyleName'
            },
            ExpressionAttributeValues={
                ':country': {'S': COUNTRY},
                ':style': {'S': style}
            }
        )
        
        # If not found in specific country, try global
        if not style_response['Items']:
            style_response = ddb_client.query(
                TableName=DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME,
                IndexName="CountryIndex",
                KeyConditionExpression='#country = :country',
                FilterExpression='#styleName = :style',
                ExpressionAttributeNames={
                    '#country': 'Country',
                    '#styleName': 'StyleName'
                },
                ExpressionAttributeValues={
                    ':country': {'S': 'global'},
                    ':style': {'S': style}
                }
            )
        
        if not style_response['Items']:
            raise Exception(f"Style {style} not found in style table for country {COUNTRY} or global")
            
        style_prompt = style_response['Items'][0].get('Prompt', {}).get('S', '')
        if not style_prompt:
            raise Exception(f"No prompt found for style {style}")
            
        print(f"style_prompt: {style_prompt}")
    except Exception as e:
        print(f"Error fetching style prompt: {str(e)}")
        raise

    # Create image generation prompt
    image_prompt = f"Full-body realistic image of a {gender} model in {style_prompt}. The model is standing in a relaxed yet confident pose, showcasing his entire figure from head to toe. Focus on the face shape, jawline, and hairstyle: {face_description}. The model is facing directly forward with a neutral expression."
    print(f"image_prompt: {image_prompt}")

    # Call Amazon Bedrock Stable Diffusion to generate the image
    max_retries = 3
    retry_count = 0
    generated_image = None
    
    while retry_count < max_retries:
        try:
            bedrock_response = bedrock.invoke_model(
                modelId='stability.sd3-5-large-v1:0',
                body=json.dumps({
                    "prompt": image_prompt,   # 필수
                    "negative_prompt": "multiple face, ugly, ugly hands, animation, cartoon, anime, manga, anime style, complex background, busy background, cluttered background",  # 선택 사항
                    "seed": random.randint(0, 4294967295), 
                    "aspect_ratio": "9:21"
                })
            )

            print(f"bedrock_response: {bedrock_response}")
            output_body = json.loads(bedrock_response.get("body").read())
            print(f"output_body: {output_body}")
            
            # finish_reasons 확인
            if "finish_reasons" in output_body and output_body["finish_reasons"][0] is None:
                base64_output_image = output_body["images"][0]
                generated_image = base64.b64decode(base64_output_image)
                break
            else:
                print(f"Image generation failed on attempt {retry_count + 1}. Reason: {output_body.get('finish_reasons', ['Unknown'])[0]}")
                retry_count += 1
                if retry_count == max_retries:
                    raise Exception(f"Failed to generate image after {max_retries} attempts. Last finish reason: {output_body.get('finish_reasons', ['Unknown'])[0]}")
                time.sleep(1)  # 재시도 전 잠시 대기
                
        except Exception as e:
            print(f"Error during image generation on attempt {retry_count + 1}: {str(e)}")
            retry_count += 1
            if retry_count == max_retries:
                raise
            time.sleep(1)

    if not generated_image:
        raise Exception("Failed to generate valid image")

    # Generate a new target object key
    query = analyze_outfit(base64_output_image)

    print(f"query: {query}")

    timestamp = int(time.time())
    target_object_key = f"images/base-image/prod/unicorn-day_{style}_stability.sd3-large-v1:0_3_{uuid}_{timestamp}.png"
    print(f"target_object_key: {target_object_key}")

    # Store the generated image in S3
    s3_client.put_object(Bucket=BUCKET_NAME, Key=target_object_key, Body=generated_image)
    print(f"Generated image stored at: {target_object_key}")

    # Prepare request body for SageMaker
    request_body = {
        'uuid': uuid,
        'bucket': BUCKET_NAME,
        'source': source_object_key,
        'target': target_object_key,  # Use the original target image path
        'output': output_object_key
    }

    # uuid and userId and theme info to ddb with proper DynamoDB types
    ddb_client.put_item(
        TableName=DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME,
        Item={
            'uuid': {'S': uuid},
            'userId': {'S': user_id},  # userId 추가
            'style': {'S': style},
            'gender': {'S': gender},
            'image_path': {'S': output_object_key},
            'story_short': {'S': ''},
            'story_short_en': {'S': ''},
            'query': {'S': query},
            'theme': {'S': ''},
            'updated_at': {"S": datetime.datetime.now().isoformat()},
            'created_at': {"S": datetime.datetime.now().isoformat()}
        }
    )

    sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_FACECHAIN_ENDPOINT_NAME,
        ContentType='application/json',
        Body=json.dumps(request_body)
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Face swap complete')
    }