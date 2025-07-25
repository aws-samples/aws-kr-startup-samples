#!/bin/bash

# CDK deployment script for observability assistant to EKS
# Usage: ./deploy_to_eks.sh <cluster-name> [region]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if cluster name is provided
if [ -z "$1" ]; then
    print_error "Cluster name is required!"
    echo "Usage: $0 <cluster-name> [region]"
    echo "Example: $0 my-eks-cluster ap-northeast-2"
    exit 1
fi

CLUSTER_NAME=$1
REGION=${2:-ap-northeast-2}

# Get account ID
print_status "Getting AWS account ID..."
ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")

print_status "Deployment Configuration:"
echo "  Cluster: $CLUSTER_NAME"
echo "  Region: $REGION"
echo "  Account: $ACCOUNT"

# Ensure we're in the CDK directory (where cdk.json is located)
cd "$(dirname "$0")"

print_status "Working directory: $(pwd)"

# Check if cluster exists
print_status "Verifying EKS cluster exists..."
if ! aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" >/dev/null 2>&1; then
    print_error "EKS cluster '$CLUSTER_NAME' not found in region '$REGION'"
    exit 1
fi

# Clean up any existing CDK output
if [ -d "cdk.out" ]; then
    print_status "Cleaning up existing CDK output..."
    rm -rf cdk.out
fi

# Suppress CDK notices and warnings
export CDK_DISABLE_VERSION_CHECK=1
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1

# Bootstrap CDK if needed
print_status "Bootstrapping CDK..."
# Check if already bootstrapped
if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region "$REGION" >/dev/null 2>&1; then
    EKS_CLUSTER_NAME=$CLUSTER_NAME cdk bootstrap aws://$ACCOUNT/$REGION --quiet
else
    print_status "CDK already bootstrapped in region $REGION"
fi

# Check if stack exists and is in failed state
print_status "Checking existing stack status..."
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name ObservabilityAssistantStack --region $REGION --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "DOES_NOT_EXIST")

if [ "$STACK_STATUS" = "ROLLBACK_COMPLETE" ] || [ "$STACK_STATUS" = "CREATE_FAILED" ]; then
    print_warning "Stack is in failed state ($STACK_STATUS). Cleaning up first..."
    aws cloudformation delete-stack --stack-name ObservabilityAssistantStack --region $REGION
    print_status "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name ObservabilityAssistantStack --region $REGION
    print_status "Stack cleanup completed."
fi

# Deploy the stack
print_status "Deploying CDK stack..."
print_warning "This may take 10-15 minutes as Docker images need to be built and pushed..."

EKS_CLUSTER_NAME=$CLUSTER_NAME cdk deploy \
    --context cluster_name=$CLUSTER_NAME \
    --context region=$REGION \
    --context account=$ACCOUNT \
    --require-approval never \
    --quiet

if [ $? -eq 0 ]; then
    print_status "CDK deployment completed successfully!"
    echo ""
    
    # Deploy Helm chart
    print_status "Deploying Helm chart to cluster: $CLUSTER_NAME in region: $REGION"
    
    # Get CDK outputs
    print_status "Getting CDK stack outputs..."
    OBSERVABILITY_IMAGE=$(aws cloudformation describe-stacks \
        --stack-name ObservabilityAssistantStack \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`ObservabilityAssistantRepoUri`].OutputValue' \
        --output text)

    TEMPO_IMAGE=$(aws cloudformation describe-stacks \
        --stack-name ObservabilityAssistantStack \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`TempoMcpServerRepoUri`].OutputValue' \
        --output text)

    POD_ROLE_ARN=$(aws cloudformation describe-stacks \
        --stack-name ObservabilityAssistantStack \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`PodRoleArn`].OutputValue' \
        --output text)

    echo "  Observability Image: $OBSERVABILITY_IMAGE"
    echo "  Tempo Image: $TEMPO_IMAGE"
    echo "  Pod Role ARN: $POD_ROLE_ARN"

    # Check if Helm is installed
    if ! command -v helm &> /dev/null; then
        print_error "Helm is not installed. Please install Helm first."
        print_status "You can install Helm by running:"
        echo "  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
        exit 1
    fi

    # Create observability namespace if it doesn't exist
    print_status "Creating observability namespace..."
    kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy Helm chart
    print_status "Deploying Helm chart..."
    helm upgrade --install observability-assistant ../helm/observability-assistant \
        --namespace observability \
        --set observabilityAssistant.image.repository=${OBSERVABILITY_IMAGE%:*} \
        --set observabilityAssistant.image.tag=latest \
        --set observabilityAssistant.image.pullPolicy=Always \
        --set observabilityAssistant.env.bedrockModelId=${BEDROCK_MODEL_ID} \
        --set observabilityAssistant.env.bedrockRegion=${BEDROCK_REGION} \
        --set tempoMcpServer.image.repository=${TEMPO_IMAGE%:*} \
        --set tempoMcpServer.image.tag=latest \
        --set tempoMcpServer.image.pullPolicy=Always \
        --set tempoMcpServer.env.tempoUrl=${TEMPO_URL} \
        --set grafanaMcpServer.image.repository=mcp/grafana \
        --set grafanaMcpServer.image.tag=latest \
        --set grafanaMcpServer.image.pullPolicy=IfNotPresent \
        --set grafanaMcpServer.env.grafanaUrl=${GRAFANA_URL} \
        --set grafanaMcpServer.env.grafanaApiKey=${GRAFANA_API_KEY} \
        --set serviceAccount.create=true \
        --set serviceAccount.name=observability-sa \
        --set aws.region=$REGION \
        --wait

    if [ $? -eq 0 ]; then
        print_status "Helm deployment completed successfully!"
        echo ""
        
        # Show deployment status
        print_status "Checking deployment status..."
        kubectl get pods -n observability
        echo ""
        kubectl get services -n observability
        echo ""
        
        print_status "Deployment completed successfully!"
        echo ""
        print_status "Next steps:"
        echo "1. Check pod logs: kubectl logs -l app.kubernetes.io/name=observability-assistant -n observability"
        echo "2. Access the service via LoadBalancer external IP"
        echo "3. Monitor the application: kubectl get pods -w -n observability"
    else
        print_error "Helm deployment failed!"
        exit 1
    fi
else
    print_error "CDK deployment failed!"
    exit 1
fi