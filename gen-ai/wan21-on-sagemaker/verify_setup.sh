#!/bin/bash

# Wan2.1 SageMaker BYOC - Setup Verification Script

echo "🔍 Verifying Wan2.1 SageMaker BYOC Setup"
echo "========================================"

# Check AWS CLI
echo "1. Checking AWS CLI configuration..."
if aws sts get-caller-identity > /dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    REGION=$(aws configure get region)
    echo "   ✅ AWS CLI configured"
    echo "   📋 Account: $ACCOUNT_ID"
    echo "   🌐 Region: ${REGION:-us-east-1}"
else
    echo "   ❌ AWS CLI not configured"
    echo "   Run: aws configure"
    exit 1
fi

# Check Docker
echo ""
echo "2. Checking Docker..."
if docker info > /dev/null 2>&1; then
    echo "   ✅ Docker is running"
else
    echo "   ❌ Docker is not running"
    echo "   Start Docker and try again"
    exit 1
fi

# Check model files
echo ""
echo "3. Checking model files..."
if [ -d "model/Wan2.1-T2V-14B" ]; then
    echo "   ✅ Model directory exists"
    
    # Check key files
    REQUIRED_FILES=("diffusion_pytorch_model.safetensors" "models_t5_umt5-xxl-enc-bf16.pth" "Wan2.1_VAE.pth")
    for file in "${REQUIRED_FILES[@]}"; do
        if [ -f "model/Wan2.1-T2V-14B/$file" ]; then
            echo "   ✅ Found: $file"
        else
            echo "   ❌ Missing: $file"
        fi
    done
    
    if [ -f "model/generate.py" ]; then
        echo "   ✅ Found: generate.py"
    else
        echo "   ❌ Missing: generate.py"
    fi
else
    echo "   ❌ Model directory not found: model/Wan2.1-T2V-14B/"
    echo "   Please place Wan2.1 model files in the model/ directory"
fi

# Check SageMaker permissions
echo ""
echo "4. Checking SageMaker permissions..."
if aws sagemaker list-endpoints > /dev/null 2>&1; then
    echo "   ✅ SageMaker access confirmed"
else
    echo "   ❌ SageMaker access denied"
    echo "   Check IAM permissions"
fi

# Check ECR permissions
echo ""
echo "5. Checking ECR permissions..."
if aws ecr describe-repositories > /dev/null 2>&1; then
    echo "   ✅ ECR access confirmed"
else
    echo "   ❌ ECR access denied"
    echo "   Check IAM permissions"
fi

# Check GPU quota
echo ""
echo "6. Checking GPU instance quota..."
echo "   ℹ️  Please verify ml.g6.2xlarge quota in AWS Service Quotas console"
echo "   ℹ️  Required: At least 1 instance for endpoint usage"

echo ""
echo "🎯 Setup Verification Complete"
echo ""
echo "If all checks passed, you can run:"
echo "   ./deploy.sh"
echo ""
echo "If any checks failed, please resolve the issues first."
