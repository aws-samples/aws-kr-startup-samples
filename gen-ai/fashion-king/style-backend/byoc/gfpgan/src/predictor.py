from flask import Flask, request, jsonify
import boto3
import os
from restore import restore_face

app = Flask(__name__)
s3_client = boto3.client('s3')


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
    output_object_key = input_data['output']
    source_path = f"/opt/workspace/source/{uuid}.png"
    output_path = f"/opt/workspace/output"
    output_file_path = f"/opt/workspace/output/restored_imgs/{uuid}.png"

    fetch_images(bucket, source_object_key, source_path)

    process_images(source_path, output_path)

    s3_client.upload_file(output_file_path, bucket, output_object_key)

    remove_all_files(source_path, output_file_path)

    return jsonify(input_data)


def fetch_images(bucket, source_object_key, source_path):
    print(f"fetch_images called")

    source_image = get_s3_image(bucket, source_object_key)

    os.makedirs(os.path.dirname(source_path), exist_ok=True)
    with open(source_path, "wb") as file:
        file.write(source_image)

    # if file is exists in source_path, then print file size
    if os.path.exists(source_path):
        print(f"source_path size: {os.path.getsize(source_path)}")


def process_images(source_path, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    restore_face(source_path, output_path)
    print(f"process_images success")


def remove_all_files(source_path, output_path):
    os.remove(source_path)
    os.remove(output_path)
    print(f"remove_all_files success")


def get_s3_image(s3_bucket, object_key):
    # Retrieve the image from S3 into memory
    print(f"get_s3_image: {s3_bucket}/{object_key}")
    response = s3_client.get_object(Bucket=s3_bucket, Key=object_key)
    return response['Body'].read()
