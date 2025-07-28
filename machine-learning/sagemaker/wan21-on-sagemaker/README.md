# Wan2.1 on SageMaker

This project is an AWS CDK application for deploying the Wan2.1 video generation model on Amazon SageMaker.

## Prerequisites

- AWS CLI configured
- AWS CDK installed
- Python 3.8 or higher
- (Recommended) Create an AWS S3 bucket and set the environment variable

## Installation & Deployment

1. **Create and activate a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate.bat  # Windows
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Create S3 bucket and set environment variable**
- Create an S3 bucket (e.g., `wan-model-bucket-<your-id>`)
- Set the environment variable:
```bash
export S3_BUCKET_NAME="<your-bucket-name>"
```

4. **Upload model file to S3 (using download_model.py)**
- On your local machine or EC2, use the following command to download the HuggingFace model and upload it to S3:
```bash
python download_model.py \
  --model-name="Wan-AI/Wan2.1-T2V-1.3B" \
  --bucket-name="$S3_BUCKET_NAME" \
  --s3-key="models/wan2.1-t2v-1.3b/model.tar.gz" \
  --region="us-east-1"
```
- For the 14B model, use `--model-name="Wan-AI/Wan2.1-T2V-14B" --s3-key="models/wan2.1-t2v-14b/model.tar.gz"`.

5. **CDK bootstrap (first time only)**
```bash
cdk bootstrap aws://ACCOUNT-NUMBER/REGION
```

6. **CDK deploy**
```bash
cdk deploy --all
```

## Endpoint Test Example

1. After the SageMaker endpoint is deployed, you can send inference requests as follows:

```python
import boto3
import json
from botocore.config import Config

boto_config = Config(connect_timeout=60, read_timeout=900)

runtime = boto3.client('sagemaker-runtime', config=boto_config)

payload = {
    "prompt": "A beautiful cat sitting in a garden",
    "task": "t2i-14B",  # or t2v-14B, t2v-1.3B, i2v-14B
    "size": "832*480"
}

response = runtime.invoke_endpoint(
    EndpointName='wan-video-endpoint',
    ContentType='application/json',
    Body=json.dumps(payload)
)

result = json.loads(response['Body'].read().decode())
print(result)
```

**Note**: Since the inference typically takes longer than 60 seconds, the client request will timeout. However, the inference continues running on the server.

2. **Check CloudWatch Logs for Results**

   To get the generated image, check the CloudWatch logs:
   
   - Go to [CloudWatch Logs](https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups)
   - Find the log group: `/aws/sagemaker/Endpoints/wan-video-endpoint`
   - Look for log entries containing:
     - `S3 upload completed: s3://your-bucket/results/...`
     - `Presigned URL generated: https://your-bucket.s3.amazonaws.com/...`
   
   The presigned URL will be valid for 1 hour and can be used to download the generated image directly.

3. **S3 Output**
- If inference is successful, the result image will be saved in the `results/` folder of your S3 bucket.
- You can also check the S3 bucket directly for the generated files.

## Notes

- The model is very large, so initial loading may take a long time.
- Video/image generation can take several minutes.
- It is recommended to use at least an ml.g6.2xlarge instance type.
- The S3 bucket name must be set as an environment variable, and both the model and output files will be stored in this bucket.