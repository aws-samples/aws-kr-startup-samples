import os
import json
import logging
import tempfile
import base64
import torch
import wan
from wan.configs import WAN_CONFIGS, SIZE_CONFIGS
from wan.utils.utils import cache_image
from pathlib import Path
from flask import Flask, request, Response
import boto3

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WanPredictor:
    def __init__(self):
        self.model_dir = "/opt/ml/model"
        self.models = {} 
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        logger.info(f"WanPredictor initialized - model path: {self.model_dir}")

    def _find_model_path(self, task):
        # Directory naming rule by task
        if task in ["t2v-14B", "t2i-14B", "i2v-14B"]:
            for name in ["Wan2.1-T2V-14B", "Wan2.1-T2I-14B", "Wan2.1-I2V-14B"]:
                if os.path.exists(os.path.join(self.model_dir, name)):
                    return os.path.join(self.model_dir, name)
        elif task == "t2v-1.3B":
            if os.path.exists(os.path.join(self.model_dir, "Wan2.1-T2V-1.3B")):
                return os.path.join(self.model_dir, "Wan2.1-T2V-1.3B")
        # fallback: first subdirectory
        for item in os.listdir(self.model_dir):
            item_path = os.path.join(self.model_dir, item)
            if os.path.isdir(item_path):
                return item_path
        return self.model_dir

    def _get_model(self, task):
        if task in self.models:
            return self.models[task]
        # Select config/class
        from wan.text2video import WanT2V
        from wan.image2video import WanI2V
        cfg = WAN_CONFIGS[task]
        model_path = self._find_model_path(task)
        if task.startswith("t2v") or task.startswith("t2i"):
            model = WanT2V(
                config=cfg,
                checkpoint_dir=model_path,
                device_id=0,
                rank=0,
                t5_fsdp=False,
                dit_fsdp=False,
                use_usp=False,
                t5_cpu=True,
            )
        elif task.startswith("i2v"):
            model = WanI2V(
                config=cfg,
                checkpoint_dir=model_path,
                device_id=0,
                rank=0,
                t5_fsdp=False,
                dit_fsdp=False,
                use_usp=False,
                t5_cpu=True,
            )
        else:
            raise ValueError(f"Unsupported task: {task}")
        self.models[task] = model
        logger.info(f"Model({task}) loaded")
        return model

    def predict(self, data):
        task = data.get("task", "t2i-14B")
        if task not in WAN_CONFIGS:
            raise ValueError(f"Unsupported task: {task}")
        prompt = data.get("prompt", "A beautiful cat sitting in a garden")
        size = data.get("size", "832*480")
        sample_shift = data.get("sample_shift", 8)
        sample_guide_scale = data.get("sample_guide_scale", 6)
        sample_steps = data.get("sample_steps", 50)
        model = self._get_model(task)
        video = model.generate(
            prompt,
            size=SIZE_CONFIGS[size],
            frame_num=1,
            shift=sample_shift,
            sampling_steps=sample_steps,
            guide_scale=sample_guide_scale,
            seed=0,
            offload_model=True
        )
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            output_file = f.name
        cache_image(
            tensor=video.squeeze(1)[None],
            save_file=output_file,
            nrow=1,
            normalize=True,
            value_range=(-1, 1)
        )

        s3_bucket = os.environ.get("S3_BUCKET_NAME")
        s3_key = f"results/{os.path.basename(output_file)}"
        s3_url = None
        presigned_url = None
        
        logger.info(f"S3_BUCKET_NAME: {s3_bucket}")
        if s3_bucket:
            s3 = boto3.client("s3")
            s3.upload_file(output_file, s3_bucket, s3_key)
            s3_url = f"s3://{s3_bucket}/{s3_key}"
            
            # Generate presigned URL for download (valid for 1 hour)
            presigned_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': s3_bucket, 'Key': s3_key},
                ExpiresIn=3600  # 1 hour
            )
            logger.info(f"S3 upload completed: {s3_url}")
            logger.info(f"Presigned URL generated: {presigned_url}")
        else:
            logger.info("S3_BUCKET_NAME not set, skipping S3 upload")

        os.unlink(output_file)
        return {
            "success": True,
            "task": task,
            "size": size,
            "s3_url": s3_url,
            "download_url": presigned_url,
            "message": "Image generated successfully. Use download_url to access the result."
        }

# Flask app creation
app = Flask(__name__)

predictor = WanPredictor()

@app.route('/ping', methods=['GET'])
def ping():
    """SageMaker health check"""
    try:
        if os.path.exists('/opt/ml/model'):
            return Response(response='\n', status=200, mimetype='application/json')
        else:
            return Response(response='\n', status=404, mimetype='application/json')
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return Response(response='\n', status=500, mimetype='application/json')

@app.route('/invocations', methods=['POST'])
def invoke():
    """SageMaker inference endpoint"""
    try:
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.data.decode('utf-8'))
        else:
            return Response(
                response=json.dumps({"error": "Unsupported content type. Please use application/json."}),
                status=415,
                mimetype='application/json'
            )
        
        # Perform inference using global predictor
        result = predictor.predict(data)
        
        # Return result
        return Response(
            response=json.dumps(result),
            status=200,
            mimetype='application/json'
        )
    
    except Exception as e:
        logger.error(f"Inference error occurred: {str(e)}")
        return Response(
            response=json.dumps({"error": str(e)}),
            status=500,
            mimetype='application/json'
        )

if __name__ == '__main__':
    # Start server
    app.run(host='0.0.0.0', port=8080)