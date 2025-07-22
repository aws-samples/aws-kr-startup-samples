# Wan2.1 14B SageMaker BYOC Deployment

Deploy Wan2.1 14B text-to-image model on Amazon SageMaker using Bring Your Own Container (BYOC) approach.

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed and running
- SageMaker execution role with ECR and S3 permissions
- GPU quota for `ml.g6.2xlarge` instances
- **S3 bucket for storing generated images** (optional but recommended)

### S3 Configuration (Optional)

To automatically save generated images to S3:

1. **Create an S3 bucket:**
   ```bash
   aws s3 mb s3://your-wan21-images-bucket
   ```

2. **Set environment variable:**
   ```bash
   export S3_BUCKET=your-wan21-images-bucket
   ```

3. **Update SageMaker execution role** with S3 permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:PutObject",
           "s3:PutObjectAcl"
         ],
         "Resource": "arn:aws:s3:::your-wan21-images-bucket/*"
       }
     ]
   }
   ```

**Note**: If S3_BUCKET is not set, images will only be returned as base64 in the API response.

### One-Command Deployment

```bash
./deploy.sh
```

This script will:
1. Build the Docker container with NVIDIA PyTorch optimized base image
2. Push the container to Amazon ECR
3. Create SageMaker model, endpoint configuration, and endpoint
4. Wait for endpoint to be in service
5. Test the endpoint with a sample request

## 📋 Manual Deployment Steps

### 1. Build and Push Container

```bash
# Build and push to ECR
./build_and_push.sh
```

### 2. Deploy to SageMaker

```bash
# Deploy model to SageMaker endpoint
python3 deploy_to_sagemaker.py
```

### 3. Test the Endpoint

```bash
# Test with sample request
python3 test_endpoint.py
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │───▶│  SageMaker       │───▶│   Docker        │
│                 │    │  Endpoint        │    │   Container     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                │                 │
                                                │ • NVIDIA PyTorch│
                                                │ • Wan2.1 14B    │
                                                │ • Flask + Nginx │
                                                └─────────────────┘
```

## 🔧 Configuration

### Instance Type
- **Recommended**: `ml.g6.2xlarge` (NVIDIA L4, 24GB VRAM)
- **Alternative**: `ml.g4dn.2xlarge` (older GPU, may have compatibility issues)

### Model Parameters
- **Task**: `t2i-14B` (text-to-image, 14B parameters)
- **Supported Sizes**: `720*1280`, `1280*720`, `480*832`, `832*480`, `1024*1024`
- **Inference Steps**: 10-50 (lower = faster, higher = better quality)
- **Guidance Scale**: 3.0-7.5 (controls prompt adherence)

## 📡 API Usage

### Endpoint Request Format

```json
{
  "prompt": "A beautiful sunset over the ocean with gentle waves",
  "task": "t2i-14B",
  "size": "1280*720",
  "num_inference_steps": 20,
  "guidance_scale": 5.0,
  "seed": 42
}
```

### Response Format

```json
{
  "status": "success",
  "image": "base64_encoded_image_data",
  "s3_url": "s3://your-bucket/wan21_images/20250722_143025_a1b2c3d4_beautiful_sunset.png",
  "s3_bucket": "your-bucket",
  "metadata": {
    "prompt": "A beautiful sunset over the ocean with gentle waves",
    "task": "t2i-14B",
    "size": "1280*720",
    "width": 1280,
    "height": 720,
    "num_inference_steps": 20,
    "guidance_scale": 5.0,
    "seed": 42,
    "method": "subprocess"
  }
}
```

**Note**: `s3_url` and `s3_bucket` fields are only included when S3_BUCKET environment variable is configured.

### Python Client Example

```python
import boto3
import json
import base64
from PIL import Image
import io

# Create SageMaker runtime client
runtime = boto3.client('sagemaker-runtime', region_name='us-east-1')

# Prepare request
payload = {
    "prompt": "A majestic mountain landscape at sunrise",
    "task": "t2i-14B",
    "size": "1280*720",
    "num_inference_steps": 25,
    "guidance_scale": 6.0,
    "seed": 123
}

# Send request
response = runtime.invoke_endpoint(
    EndpointName='your-endpoint-name',
    ContentType='application/json',
    Body=json.dumps(payload)
)

# Parse response
result = json.loads(response['Body'].read().decode())
if result['status'] == 'success':
    # Decode and save image
    image_data = base64.b64decode(result['image'])
    image = Image.open(io.BytesIO(image_data))
    image.save('generated_image.png')
```

## 🐳 Container Details

### Base Image
- **NVIDIA PyTorch 24.02**: `nvcr.io/nvidia/pytorch:24.02-py3`
- **PyTorch Version**: 2.3.0a0+ebedce2
- **CUDA**: 12.3 with forward compatibility

### Key Components
- **Web Server**: Nginx + Gunicorn + Flask
- **Model Handler**: Optimized inference pipeline
- **Health Checks**: `/ping` and `/health` endpoints
- **Inference**: `/invocations` endpoint

### Performance Characteristics
- **Cold Start**: ~10 minutes (model loading)
- **Inference Time**: ~3-4 minutes per image (14B model)
- **Memory Usage**: ~20GB VRAM for 14B model
- **Concurrent Requests**: 1 (due to memory constraints)

## 📊 Performance Optimization

### Current Limitations
- Model loads from disk for each request (subprocess method)
- No model caching between requests
- Single-threaded inference

### Potential Improvements
- In-memory model loading (requires Wan2.1 Python API)
- Model server pattern with persistent processes
- Batch processing for multiple requests
- Smaller model variants (1.3B) for faster inference

## 🔍 Monitoring

### CloudWatch Logs
```bash
# View endpoint logs
aws logs get-log-events \
  --log-group-name "/aws/sagemaker/Endpoints/your-endpoint-name" \
  --log-stream-name "AllTraffic/instance-id"
```

### Health Check
```bash
curl -X GET https://runtime.sagemaker.region.amazonaws.com/endpoints/your-endpoint-name/ping
```

## 🛠️ Troubleshooting

### Common Issues

1. **CUDA Compatibility Error**
   - Solution: Use `ml.g6.2xlarge` instead of `ml.g4dn.2xlarge`
   - Root cause: Older GPU drivers incompatible with PyTorch 2.3+

2. **Model Loading Timeout**
   - Solution: Increase endpoint timeout to 10+ minutes
   - Root cause: 14B model takes time to load from disk

3. **Out of Memory Error**
   - Solution: Use `ml.g6.2xlarge` with 24GB VRAM
   - Root cause: 14B model requires significant GPU memory

4. **Invalid Size Parameter**
   - Solution: Use supported sizes: `720*1280`, `1280*720`, `480*832`, `832*480`, `1024*1024`
   - Root cause: Wan2.1 has predefined aspect ratios

### Debug Commands

```bash
# Check container logs
docker logs container-name

# Test locally
cd local_test
./serve_local.sh wan21-14b-sagemaker-byoc:latest

# Performance test
python3 local_test/performance_test.py
```

## 📁 Project Structure

```
wan2.1-sagemaker-byoc/
├── README.md                 # This file
├── deploy.sh                 # One-command deployment script
├── build_and_push.sh         # Container build and ECR push
├── deploy_to_sagemaker.py    # SageMaker deployment script
├── test_endpoint.py          # Endpoint testing script
├── Dockerfile                # Container definition
├── requirements.txt          # Python dependencies
├── code/                     # Inference code
│   ├── predictor.py          # Flask application
│   ├── model_handler.py      # Model inference logic
│   ├── serve                 # Container entry point
│   └── nginx.conf            # Web server configuration
├── model/                    # Model files (not in repo)
│   ├── Wan2.1-T2V-14B/       # Model weights and config
│   └── generate.py           # Generation script
└── local_test/               # Local testing utilities
    ├── serve_local.sh        # Local container testing
    ├── performance_test.py   # Performance benchmarking
    └── test_dir/             # Test data directory
```

## 🔐 Security Considerations

- Model files are not included in the repository (too large)
- Use IAM roles with minimal required permissions
- Enable VPC endpoints for private communication
- Consider encryption at rest and in transit

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues and questions:
- Create an issue in this repository
- Check CloudWatch logs for debugging
- Refer to AWS SageMaker documentation

---

**Note**: This implementation uses the subprocess method for model inference. For production use, consider implementing in-memory model loading for better performance.
