#!/usr/bin/env python

import os
import tempfile
import subprocess
import multiprocessing
import boto3
import signal
import sys
from flask import Flask, request, jsonify, Response
from utils import load_model, generate_image, generate_video
from wan.utils.utils import cache_image, cache_video

base_model = None

def get_model(task):
    """Model return - lazy loading on first request"""
    global base_model
    
    if base_model is None:
        print("Initializing model on first request...")
        model_path = "/opt/ml/model/Wan2.1-T2V-1.3B"
        print(f"Loading base model from {model_path}")
        
        base_model = load_model("t2i-14B", model_path, offload_model=True, t5_cpu=False)
        print("Base model loaded successfully")
    
    return base_model

def upload_to_s3(file_path):
    """S3 upload and URL return"""
    bucket = os.environ.get("S3_BUCKET_NAME")
    if not bucket:
        return None, None
    
    s3 = boto3.client("s3")
    key = f"results/{os.path.basename(file_path)}"
    s3.upload_file(file_path, bucket, key)
    
    url = s3.generate_presigned_url('get_object', 
                                   Params={'Bucket': bucket, 'Key': key}, 
                                   ExpiresIn=3600)
    return f"s3://{bucket}/{key}", url

# Flask app
app = Flask(__name__)

@app.route('/ping', methods=['GET'])
def ping():
    return Response(status=200)

@app.route('/invocations', methods=['POST'])
def invoke():
    try:
        data = request.get_json()
        task = data.get("task", "t2v-1.3B")
        prompt = data.get("prompt", "A beautiful scene")
        size = data.get("size", "480*832")
        
        # Check supported tasks
        supported_tasks = ["t2v-1.3B", "t2i-14B", "vace-1.3B"]
        if task not in supported_tasks:
            return jsonify({"error": f"Unsupported task: {task}. Supported: {supported_tasks}"}), 400
        
        model = get_model(task)
        
        # Generate video or image based on task
        if task.startswith("t2v") or task.startswith("vace"):
            result = generate_video(model, prompt, size, 
                                  data.get("sample_steps", 30),
                                  data.get("guide_scale", 6),
                                  data.get("shift", 8))
            
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                output_file = f.name
            
            normalized = (result + 1) / 2
            cache_video(normalized.unsqueeze(0), output_file, fps=8, 
                       normalize=False, value_range=(0, 1))
                       
        elif task.startswith("t2i"):
            result = generate_image(model, prompt, size,
                                  data.get("sample_steps", 30),
                                  data.get("guide_scale", 6),
                                  data.get("shift", 8))
                                  
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                output_file = f.name
                
            cache_image(result.squeeze(1)[None], output_file, 
                       normalize=True, value_range=(-1, 1))
        
        s3_url, download_url = upload_to_s3(output_file)
        os.unlink(output_file)
        
        return jsonify({
            "success": True,
            "task": task,
            "s3_url": s3_url,
            "download_url": download_url
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

def sigterm_handler(nginx_pid, gunicorn_pid):
    """Gracefully shut down the processes."""
    try:
        os.kill(nginx_pid, signal.SIGQUIT)
    except OSError:
        pass
    try:
        os.kill(gunicorn_pid, signal.SIGTERM)
    except OSError:
        pass
    sys.exit(0)

def start_server():
    """Start server"""
    print("Starting SageMaker inference server...")
    
    subprocess.check_call(['ln', '-sf', '/dev/stdout', '/var/log/nginx/access.log'])
    subprocess.check_call(['ln', '-sf', '/dev/stderr', '/var/log/nginx/error.log'])
    
    workers = 1
    print(f"Using {workers} sync worker for GPU inference (lazy loading)")
    
    nginx = subprocess.Popen(['nginx', '-c', '/opt/ml/code/nginx.conf'])
    gunicorn = subprocess.Popen([
        'gunicorn',
        '--timeout', '1200',
        '-k', 'sync',              # sync worker (CUDA compatibility)
        '-b', 'unix:/tmp/gunicorn.sock',
        '-w', str(workers),       
        '--max-requests', '1000',
        '--max-requests-jitter', '100',
        'wsgi:app'
    ])
    
    # Set up termination signal handler
    signal.signal(signal.SIGTERM, lambda a, b: sigterm_handler(nginx.pid, gunicorn.pid))
    
    # Exit server when either process terminates
    pids = {nginx.pid, gunicorn.pid}
    while True:
        pid, _ = os.wait()
        if pid in pids:
            break
            
    sigterm_handler(nginx.pid, gunicorn.pid)
    print('Inference server exiting')

if __name__ == '__main__':
    start_server()