#!/bin/bash

# Cleanup script for observability assistant CDK deployment
# Usage: ./cleanup.sh <cluster-name> [region]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

print_warning "This will destroy the CDK stack and all associated resources!"
print_status "Cluster: $CLUSTER_NAME"
print_status "Region: $REGION"
print_status "Account: $ACCOUNT"

read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Cleanup cancelled."
    exit 0
fi

# Ensure we're in the CDK directory
cd "$(dirname "$0")"

# Suppress CDK notices
export CDK_DISABLE_VERSION_CHECK=1
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1

# Clean up Helm deployment first
print_status "Cleaning up Helm deployment..."
if command -v helm &> /dev/null; then
    if helm list -n observability | grep -q observability-assistant; then
        helm uninstall observability-assistant -n observability
        print_status "Helm chart uninstalled successfully"
    else
        print_status "Helm chart not found, skipping"
    fi
else
    print_warning "Helm not found, skipping Helm cleanup"
fi

print_status "Destroying CDK stack..."
cdk destroy \
    --context cluster_name=$CLUSTER_NAME \
    --context region=$REGION \
    --context account=$ACCOUNT \
    --force \
    --quiet

if [ $? -eq 0 ]; then
    print_status "Cleanup completed successfully!"
    print_warning "Note: ECR repositories may still contain images that incur storage costs."
    print_status "To clean up ECR repositories manually:"
    echo "  aws ecr delete-repository --repository-name observability-assistant/agent --force --region $REGION"
    echo "  aws ecr delete-repository --repository-name observability-assistant/tempo-mcp-server --force --region $REGION"
else
    print_error "Cleanup failed!"
    exit 1
fi