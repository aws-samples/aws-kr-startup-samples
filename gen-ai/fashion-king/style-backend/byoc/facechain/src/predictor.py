from flask import Flask, request, jsonify
import boto3
import subprocess
import os
import cv2
import argparse
from modelscope.outputs import OutputKeys
from modelscope.pipelines import pipeline

app = Flask(__name__)
s3_client = boto3.client('s3')

IMAGE_FACE_FUSION = pipeline('face_fusion_torch',
                                model='damo/cv_unet_face_fusion_torch', 
                                model_revision='v1.0.3')

def face_fusion(user_path, template_path, output_path):               
    result = IMAGE_FACE_FUSION(dict(template=template_path, user=user_path))
    print(f"face_fusion result: {result}")
    
    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 디버깅을 위한 추가 정보 출력
    output_img = result[OutputKeys.OUTPUT_IMG]
    print(f"Output image shape: {output_img.shape}")
    print(f"Output image dtype: {output_img.dtype}")
    print(f"Output path permissions: {oct(os.stat(os.path.dirname(output_path)).st_mode)[-3:]}")
    
    # 이미지 저장 시도 및 결과 확인
    success = cv2.imwrite(output_path, output_img)
    print(f"cv2.imwrite success: {success}")
    
    # 파일이 실제로 생성되었는지 확인
    if not os.path.exists(output_path):
        raise RuntimeError(f"Image file was not created at {output_path}")
    print(f"output_path size: {os.path.getsize(output_path)}")

@app.route('/ping', methods=['GET'])
def ping():
    health = True  # You can implement health check logic here
    status = 200 if health else 404
    return '', status


@app.route('/invocations', methods=['POST'])
def invocations():
    input_data = request.get_json(force=True)

    uuid = input_data['uuid']
    bucket = input_data['bucket']
    source_object_key = input_data['source']
    target_object_key = input_data['target']
    output_object_key = input_data['output']
    source_path = f"/opt/program/workspace/source/{uuid}.png"
    target_path = f"/opt/program/workspace/target/{uuid}.png"
    output_path = f"/opt/program/workspace/output/{uuid}.png"

    fetch_images(bucket, source_object_key, source_path, target_object_key, target_path)

    process_images(source_path, target_path, output_path)
    print("process_images finished")

    s3_client.upload_file(output_path, bucket, output_object_key)
    print("upload_file finished")

    remove_all_files(source_path, target_path, output_path)
    print("remove_all_files finished")

    return jsonify(input_data)


def fetch_images(bucket, source_object_key, source_path, target_object_key, target_path):
    print(f"fetch_images called")

    source_image = get_s3_image(bucket, source_object_key)
    target_image = get_s3_image(bucket, target_object_key)

    os.makedirs(os.path.dirname(source_path), exist_ok=True)
    with open(source_path, "wb") as file:
        file.write(source_image)

    # if file is exists in source_path, then print file size
    if os.path.exists(source_path):
        print(f"source_path size: {os.path.getsize(source_path)}")

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "wb") as file:
        file.write(target_image)

    # if file is exists in target_path, then print file size
    if os.path.exists(target_path):
        print(f"target_path size: {os.path.getsize(target_path)}")


def process_images(source_path, target_path, output_path):
    print(f"process_images called")
    print(f"source_path: {source_path}")
    print(f"target_path: {target_path}")
    print(f"output_path: {output_path}")
    face_fusion(source_path, target_path, output_path)


def remove_all_files(source_path, target_path, output_path):
    os.remove(source_path)
    os.remove(target_path)
    os.remove(output_path)


def get_s3_image(s3_bucket, object_key):
    # Retrieve the image from S3 into memory
    print(f"get_s3_image: {s3_bucket}/{object_key}")
    response = s3_client.get_object(Bucket=s3_bucket, Key=object_key)
    return response['Body'].read()
