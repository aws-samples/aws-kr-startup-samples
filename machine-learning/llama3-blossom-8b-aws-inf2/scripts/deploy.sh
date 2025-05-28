#!/bin/bash
# deploy.sh - Enhanced deployment script with model configuration support

set -e

# Display usage information
function show_usage {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --model-name=NAME         Set the SageMaker model name"
    echo "  --endpoint-name=NAME      Set the SageMaker endpoint name"
    echo "  --instance-type=TYPE      Set the instance type (e.g., ml.inf2.xlarge)"
    echo "  --instance-count=N        Set the number of instances (e.g., 1, 2)"
    echo "  --volume-size=N           Set the volume size in GB (e.g., 64, 128)"
    echo "  --health-check-timeout=N  Set the health check timeout in seconds"
    echo "  --bucket-name=NAME        Set the S3 bucket name (default: sagemaker-llm-<region>-<account>)"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  $0 --instance-type=ml.inf2.2xlarge --instance-count=2"
    echo "  $0 --model-name=my-custom-model --endpoint-name=my-endpoint"
    echo "  $0 --bucket-name=my-custom-bucket"
    exit 1
}

# Get current AWS account and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_DEFAULT_REGION:-us-west-2}

# Model and endpoint configuration (can be overridden with command-line options)
# Default values from CDK configuration
MODEL_NAME="llama3-blsm-8b"
ENDPOINT_NAME=""  # Will be auto-generated if not specified
INSTANCE_TYPE="ml.inf2.xlarge"
INSTANCE_COUNT="1"
VOLUME_SIZE="64"
HEALTH_CHECK_TIMEOUT="600"

# S3 bucket configuration
DEFAULT_BUCKET_PREFIX="sagemaker-llm"
BUCKET_NAME="${DEFAULT_BUCKET_PREFIX}-${REGION}-${ACCOUNT_ID}"


# Parse command-line options
while [[ $# -gt 0 ]]; do
  case $1 in
    --model-name=*)
      MODEL_NAME="${1#*=}"
      shift
      ;;
    --endpoint-name=*)
      ENDPOINT_NAME="${1#*=}"
      shift
      ;;
    --instance-type=*)
      INSTANCE_TYPE="${1#*=}"
      shift
      ;;
    --instance-count=*)
      INSTANCE_COUNT="${1#*=}"
      shift
      ;;
    --volume-size=*)
      VOLUME_SIZE="${1#*=}"
      shift
      ;;
    --health-check-timeout=*)
      HEALTH_CHECK_TIMEOUT="${1#*=}"
      shift
      ;;
    --bucket-name=*)
      BUCKET_NAME="${1#*=}"
      shift
      ;;
    *)
      # Unknown option
      echo "❌ Unknown option: $1"
      show_usage
      ;;
  esac
done

echo "🚀 Starting SageMaker LLM Endpoint deployment..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS CLI is not configured. Please run 'aws configure' first."
    exit 1
fi

# Get current AWS account and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_DEFAULT_REGION:-us-west-2}
STACK_NAME="SageMakerLLM"

echo "📋 Deployment Information:"
echo "   Account ID: $ACCOUNT_ID"
echo "   Region: $REGION"
echo "   Stack Name: $STACK_NAME"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
python -m pip install -r requirements.txt

# Download model from Hugging Face
echo "📥 Downloading model from Hugging Face..."
python download_model.py

# Export bucket name for CDK and package_model.py
export CDK_BUCKET_NAME="$BUCKET_NAME"
export MODEL_BUCKET_NAME="$BUCKET_NAME"

# Package model and upload to S3 (bucket will be created if needed)
echo "📦 Packaging model and uploading to S3..."
python package_model.py

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Bootstrap CDK (if not already done)
echo "🔧 Bootstrapping CDK..."
npx cdk bootstrap aws://$ACCOUNT_ID/$REGION

# Build TypeScript
echo "🏗️ Building TypeScript..."
npm run build

# Print configuration parameters
echo "Configuration:"
echo "   S3 Bucket: $BUCKET_NAME"
echo "   Model Name: $MODEL_NAME"
echo "   Endpoint Name: ${ENDPOINT_NAME:-auto-generated}"
echo "   Instance Type: $INSTANCE_TYPE"
echo "   Instance Count: $INSTANCE_COUNT"
echo "   Volume Size: $VOLUME_SIZE GB"
echo "   Health Check Timeout: $HEALTH_CHECK_TIMEOUT seconds"

# Export configuration for CDK
export CDK_MODEL_NAME=$MODEL_NAME
export CDK_ENDPOINT_NAME=$ENDPOINT_NAME
export CDK_INSTANCE_TYPE=$INSTANCE_TYPE
export CDK_INSTANCE_COUNT=$INSTANCE_COUNT
export CDK_VOLUME_SIZE=$VOLUME_SIZE
export CDK_HEALTH_CHECK_TIMEOUT=$HEALTH_CHECK_TIMEOUT

# Synthesize CloudFormation template
echo "📄 Synthesizing CloudFormation template..."
npx cdk synth

# Show diff if stack exists
echo "🔍 Checking for changes..."
npx cdk diff || true

# Deploy the stack
echo "🚢 Deploying stack..."
npx cdk deploy --require-approval never

echo "✅ Deployment completed successfully!"
echo ""
echo "🔍 You can check the deployment status in the AWS Console:"
echo "   SageMaker: https://$REGION.console.aws.amazon.com/sagemaker/home?region=$REGION#/endpoints"
echo "   CloudFormation: https://$REGION.console.aws.amazon.com/cloudformation/home?region=$REGION#/stacks"

# cleanup.sh - Cleanup script
echo ""
# Get endpoint name from stack outputs
echo "📡 Getting endpoint information..."
ENDPOINT_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='EndpointName'].OutputValue" \
    --output text 2>/dev/null || echo "")

if [ -n "$ENDPOINT_NAME" ]; then
    echo "   Endpoint Name: $ENDPOINT_NAME"
    echo ""
    echo "🧪 To test the endpoint, run:"
    echo "   python test/test_endpoint.py $ENDPOINT_NAME"
else
    echo "   ⚠️ Could not retrieve endpoint name. Check CloudFormation outputs."
fi

echo ""
echo "📝 To clean up resources later, run:"
echo "   ./scripts/cleanup.sh"

# cleanup.sh - Enhanced cleanup script
cat > scripts/cleanup.sh << 'EOF'
#!/bin/bash
# cleanup.sh - Simple cleanup script

set -e

STACK_NAME="SageMakerLLM"

echo "🧹 Cleaning up SageMaker LLM Endpoint resources..."

# Check if stack exists
if aws cloudformation describe-stacks --stack-name $STACK_NAME &>/dev/null; then
    echo "🗑️ Destroying CDK stack: $STACK_NAME"
    npx cdk destroy $STACK_NAME --force
    echo "✅ Cleanup completed successfully!"
else
    echo "ℹ️ Stack $STACK_NAME does not exist. Nothing to clean up."
fi
EOF

chmod +x scripts/cleanup.sh
