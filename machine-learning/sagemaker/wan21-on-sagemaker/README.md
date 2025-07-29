# WAN 2.1 on Amazon SageMaker

A production-ready deployment of the WAN 2.1 (Video Generation AI) model on Amazon SageMaker using AWS CDK. This project provides a scalable, GPU-optimized inference endpoint for text-to-video and text-to-image generation.

## 🎥 Features

- **Text-to-Video Generation**: High-quality video generation from text prompts
- **Text-to-Image Generation**: Single frame image generation
- **GPU-Optimized**: Leverages CUDA acceleration with memory optimization
- **Lazy Loading**: Fast cold start with on-demand model loading
- **Auto-Scaling**: SageMaker endpoint with configurable scaling policies
- **S3 Integration**: Automatic result storage and presigned URL generation
- **Production Ready**: Docker-based deployment with health checks

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client API    │───▶│  SageMaker      │───▶│   S3 Storage    │
│   Request       │    │  Endpoint       │    │   Results       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  GPU Instance   │
                       │  WAN 2.1 Model  │
                       │  (ml.g6.2xlarge)│
                       └─────────────────┘
```

## 📁 Project Structure

```
wan21-on-sagemaker/
├── app.py                      # CDK application entry point
├── cdk_stacks/                 # AWS CDK infrastructure stacks
│   ├── sm_execution_role.py    # SageMaker execution role
│   ├── sm_model.py             # SageMaker model definition
│   ├── sm_endpoint_config.py   # Endpoint configuration
│   └── sm_endpoint.py          # SageMaker endpoint
├── inference_code/             # Model serving code
│   ├── serve.py                # Main inference server
│   ├── utils.py                # Model loading and generation utilities
│   ├── wsgi.py                 # WSGI application entry
│   ├── Dockerfile              # Container definition
│   ├── nginx.conf              # Nginx configuration
│   ├── requirements.txt        # Python dependencies
│   └── wan/                    # WAN model implementation
│       ├── text2video.py       # Text-to-video generation
│       ├── image2video.py      # Image-to-video generation
│       ├── vace.py             # VACE model implementation
│       ├── configs/            # Model configurations
│       ├── modules/            # Model components
│       ├── utils/              # Utility functions
│       └── distributed/        # Distributed training support
├── download_model.py           # HuggingFace model download script
├── request_payload.json        # API request example
└── requirements.txt            # CDK dependencies
```

## 🚀 Quick Start

### Prerequisites

- **AWS CLI** configured with appropriate permissions
- **AWS CDK** v2 installed (`npm install -g aws-cdk`)
- **Python 3.10+** 
- **Docker** (for local testing)
- **GPU-enabled AWS region** (us-east-1, us-west-2, etc.)

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd wan21-on-sagemaker

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure S3 Bucket

```bash
# Create S3 bucket for model artifacts and results
export S3_BUCKET_NAME="wan-model-bucket-$(whoami)-$(date +%s)"
aws s3 mb s3://$S3_BUCKET_NAME

# Set environment variable
echo "export S3_BUCKET_NAME=$S3_BUCKET_NAME"
```

### 3. Download and Upload Model

```bash
# Download WAN 2.1 model (1.3B - recommended for testing)
python download_model.py \
  --model-name="Wan-AI/Wan2.1-T2V-1.3B" \
  --bucket-name="$S3_BUCKET_NAME" \
  --s3-key="models/wan2.1-t2v-1.3b/model.tar.gz" \
  --region="us-east-1"

# For 14B model (requires larger instances)
python download_model.py \
  --model-name="Wan-AI/Wan2.1-T2V-14B" \
  --bucket-name="$S3_BUCKET_NAME" \
  --s3-key="models/wan2.1-t2v-14b/model.tar.gz" \
  --region="us-east-1"
```

### 4. Deploy Infrastructure

```bash
# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy all stacks
cdk deploy --all --require-approval never

# Get endpoint name
ENDPOINT_NAME=$(aws cloudformation describe-stacks \
  --stack-name WanVideoEndpointStack \
  --query 'Stacks[0].Outputs[?OutputKey==`EndpointName`].OutputValue' \
  --output text)

echo "Endpoint deployed: $ENDPOINT_NAME"
```

## 🔧 API Usage

### Supported Tasks

| Task       | Description | Model Size | Output |
|------------|-------------|------------|---------|
| `t2i-14B`  | Text to Image | 14B params | Single image | (Current Version)
| `t2v-1.3B` | Text to Video | 1.3B params | 81-frame video |
| `vace-1.3B`| Video Continuation | 1.3B params | Extended video |

### API Request Format

```json
{
  "task": "t2i-14B",
  "prompt": "A beautiful cat sitting in a garden, cinematic, 4k",
  "size": "1280*720",
  "sample_steps": 30,
  "guide_scale": 6.0,
  "shift": 8.0
}
```

### Example API Calls
After endpoint deployment, a timeout error may occur during the first call due to model loading. Subsequent calls will respond within approximately 30 seconds.RetryClaude can make mistakes. Please double-check responses.

```bash
# Text-to-Image Generation
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name $ENDPOINT_NAME \
  --content-type "application/json" \
  --body '{
    "task": "t2i-14B",
    "prompt": "A majestic dragon flying over mountains, fantasy art",
    "size": "1280*720",
    "sample_steps": 30
  }' \
  output.json
```

### Response Format

```json 
{
    "ContentType": "application/json",
    "InvokedProductionVariant": "AllTraffic"
}
```

### Common Issues

**CUDA Out of Memory**
```bash
# Solution: Reduce resolution or use smaller model
"size": "960*544"  # Instead of "1280*720" 
```

**Slow Inference**
```bash
# Solution: Reduce sampling steps
"sample_steps": 20  # Instead of 30
```

**Cold Start Timeouts**
```bash
# Solution: Health check excludes model loading
# First request may take 60-90 seconds
```