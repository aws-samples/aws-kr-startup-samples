#!/bin/bash

# Build and push script for Wan2.1 14B SageMaker BYOC

set -e

# Configuration
ALGORITHM_NAME="wan21-14b-sagemaker-byoc"
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "🚀 Starting Wan2.1 14B BYOC Build and Push"
echo "Algorithm: ${ALGORITHM_NAME}"
echo "Region: ${REGION}"

# Get AWS account ID
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to get AWS account ID. Make sure AWS CLI is configured."
    exit 1
fi

# Full ECR repository name
FULLNAME="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${ALGORITHM_NAME}:latest"

echo "📦 Building Docker image: ${FULLNAME}"

# Check if ECR repository exists, create if not
echo "🔍 Checking ECR repository..."
aws ecr describe-repositories --repository-names "${ALGORITHM_NAME}" --region ${REGION} > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "📝 Creating ECR repository: ${ALGORITHM_NAME}"
    aws ecr create-repository --repository-name "${ALGORITHM_NAME}" --region ${REGION} > /dev/null
    echo "✅ ECR repository created"
else
    echo "✅ ECR repository already exists"
fi

# Get ECR login token and login to Docker
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${FULLNAME}

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to login to ECR"
    exit 1
fi

# Build the docker image
echo "🔨 Building Docker image..."
docker build -t ${ALGORITHM_NAME} .

if [ $? -ne 0 ]; then
    echo "❌ Error: Docker build failed"
    exit 1
fi

# Tag the image
echo "🏷️  Tagging image..."
docker tag ${ALGORITHM_NAME} ${FULLNAME}

# Push the image to ECR
echo "📤 Pushing image to ECR..."
docker push ${FULLNAME}

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to push image to ECR"
    exit 1
fi

echo "✅ Successfully built and pushed ${FULLNAME}"
echo ""
echo "🎯 Image URI: ${FULLNAME}"
echo ""
echo "📋 Next: Deploying to SageMaker..."
