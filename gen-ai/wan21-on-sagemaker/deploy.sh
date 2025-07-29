#!/bin/bash

# Wan2.1 14B SageMaker BYOC - One-Command Deployment Script
# This script builds, pushes, and deploys the Wan2.1 model to SageMaker

set -e  # Exit on any error

echo "🚀 Wan2.1 14B SageMaker BYOC Deployment"
echo "========================================"

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if model files exist
if [ ! -d "model/Wan2.1-T2V-14B" ]; then
    echo "❌ Model files not found in model/Wan2.1-T2V-14B/"
    echo "   Please ensure Wan2.1 model files are properly placed."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Get AWS account and region info
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
REGION=${REGION:-us-east-1}

echo "📋 Deployment Configuration:"
echo "   AWS Account: $ACCOUNT_ID"
echo "   AWS Region: $REGION"
echo "   Instance Type: ml.g6.2xlarge"
if [ -n "$S3_BUCKET" ]; then
    echo "   S3 Bucket: $S3_BUCKET (images will be saved to S3)"
else
    echo "   S3 Bucket: Not configured (images will only be returned as base64)"
fi

# Step 1: Build and push container
echo ""
echo "🔨 Step 1: Building and pushing Docker container..."
echo "=================================================="

if ! ./build_and_push.sh; then
    echo "❌ Container build and push failed"
    exit 1
fi

echo "✅ Container build and push completed"

# Step 2: Deploy to SageMaker
echo ""
echo "🚀 Step 2: Deploying to SageMaker..."
echo "===================================="

export AWS_DEFAULT_REGION=$REGION

if ! python3 deploy_to_sagemaker.py; then
    echo "❌ SageMaker deployment failed"
    exit 1
fi

echo "✅ SageMaker deployment completed"

# Step 3: Test the endpoint
echo ""
echo "🧪 Step 3: Testing the endpoint..."
echo "=================================="

if [ -f "endpoint_info.json" ]; then
    echo "⏳ Waiting 30 seconds for endpoint to fully initialize..."
    sleep 30
    
    echo "🔍 Running endpoint test..."
    if python3 test_endpoint.py; then
        echo "✅ Endpoint test completed successfully"
    else
        echo "⚠️  Endpoint test failed, but deployment was successful"
        echo "   The endpoint may need more time to warm up"
        echo "   Try testing again in a few minutes"
    fi
else
    echo "⚠️  Endpoint info file not found, skipping test"
fi

# Final summary
echo ""
echo "🎉 DEPLOYMENT SUMMARY"
echo "===================="

if [ -f "endpoint_info.json" ]; then
    ENDPOINT_NAME=$(python3 -c "import json; print(json.load(open('endpoint_info.json'))['endpoint_name'])")
    ENDPOINT_ARN=$(python3 -c "import json; print(json.load(open('endpoint_info.json'))['endpoint_arn'])")
    
    echo "✅ Deployment Status: SUCCESS"
    echo "📍 Endpoint Name: $ENDPOINT_NAME"
    echo "🔗 Endpoint ARN: $ENDPOINT_ARN"
    echo "🌐 Region: $REGION"
    echo ""
    echo "📡 API Usage:"
    echo "   aws sagemaker-runtime invoke-endpoint \\"
    echo "     --endpoint-name $ENDPOINT_NAME \\"
    echo "     --content-type application/json \\"
    echo "     --body '{\"prompt\":\"A beautiful landscape\",\"task\":\"t2i-14B\",\"size\":\"1280*720\"}' \\"
    echo "     response.json"
    echo ""
    echo "🔍 Monitor logs:"
    echo "   aws logs get-log-events \\"
    echo "     --log-group-name \"/aws/sagemaker/Endpoints/$ENDPOINT_NAME\" \\"
    echo "     --log-stream-name \"AllTraffic/\$(instance-id)\""
    echo ""
    echo "💰 Cost Estimate: ~\$1.50/hour for ml.g6.2xlarge instance"
    echo "⚠️  Remember to delete the endpoint when not in use to avoid charges!"
    echo ""
    echo "🗑️  Cleanup command:"
    echo "   aws sagemaker delete-endpoint --endpoint-name $ENDPOINT_NAME"
else
    echo "❌ Deployment Status: FAILED"
    echo "   Check the logs above for error details"
    exit 1
fi

echo ""
echo "🚀 Deployment completed successfully!"
echo "   Your Wan2.1 14B model is now available on SageMaker!"
