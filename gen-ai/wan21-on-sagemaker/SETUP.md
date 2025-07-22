# Setup Instructions

## Prerequisites

### 1. AWS Account Setup
- AWS account with SageMaker access
- AWS CLI installed and configured
- Appropriate IAM permissions

### 2. Required IAM Permissions
Your AWS user/role needs these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sagemaker:*",
                "ecr:*",
                "iam:PassRole",
                "s3:GetObject",
                "s3:PutObject",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:GetLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
```

### 3. SageMaker Execution Role
Create a SageMaker execution role with these policies:
- `AmazonSageMakerFullAccess`
- `AmazonEC2ContainerRegistryFullAccess`
- Custom policy for S3 access (if needed)

### 4. GPU Instance Quota
Request quota increase for `ml.g6.2xlarge` instances:
- Go to AWS Service Quotas console
- Search for "SageMaker"
- Find "ml.g6.2xlarge for endpoint usage"
- Request increase to at least 1 instance

### 5. Docker Setup
```bash
# Install Docker (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install docker.io
sudo usermod -aG docker $USER
# Log out and back in

# Verify Docker installation
docker --version
docker info
```

### 6. Model Files
You need to obtain Wan2.1 model files and place them in the `model/` directory:
```
model/
├── Wan2.1-T2V-14B/
│   ├── diffusion_pytorch_model.safetensors
│   ├── models_t5_umt5-xxl-enc-bf16.pth
│   ├── Wan2.1_VAE.pth
│   └── config.json
├── generate.py
└── other_model_files...
```

**Note**: Model files are not included in this repository due to size constraints.

## Quick Setup Commands

```bash
# 1. Clone repository
git clone <repository-url>
cd wan2.1-sagemaker-byoc

# 2. Configure AWS CLI
aws configure
# Enter your Access Key ID, Secret Access Key, Region, and Output format

# 3. Verify AWS configuration
aws sts get-caller-identity

# 4. Check Docker
docker info

# 5. Place model files in model/ directory
# (Download Wan2.1 model files separately)

# 6. Deploy to SageMaker
./deploy.sh
```

## Troubleshooting

### Common Issues

1. **Permission Denied (Docker)**
   ```bash
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

2. **AWS CLI Not Configured**
   ```bash
   aws configure
   # Or set environment variables:
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_DEFAULT_REGION=us-east-1
   ```

3. **SageMaker Execution Role Not Found**
   - Create role in IAM console
   - Attach required policies
   - Update `deploy_to_sagemaker.py` with correct role ARN

4. **GPU Quota Exceeded**
   - Request quota increase in AWS Service Quotas
   - Wait for approval (usually 24-48 hours)

5. **Model Files Missing**
   - Ensure all required model files are in `model/` directory
   - Check file permissions and sizes

### Verification Commands

```bash
# Check AWS configuration
aws sts get-caller-identity
aws sagemaker list-endpoints

# Check Docker
docker --version
docker images

# Check model files
ls -la model/Wan2.1-T2V-14B/

# Test local deployment
cd local_test
./serve_local.sh wan21-14b-sagemaker-byoc:latest
```

## Cost Estimation

- **ml.g6.2xlarge**: ~$1.50/hour
- **Data transfer**: Minimal for inference
- **Storage**: ECR storage costs

**Important**: Remember to delete endpoints when not in use to avoid ongoing charges!

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review CloudWatch logs
3. Create an issue in the repository
4. Consult AWS SageMaker documentation
