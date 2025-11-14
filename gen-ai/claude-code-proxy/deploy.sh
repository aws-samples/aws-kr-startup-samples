#!/bin/bash
set -e

echo "🚀 Deploying Claude Code Proxy to Fargate..."

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "❌ AWS CDK CLI not found. Install it with: npm install -g aws-cdk"
    exit 1
fi

# Setup Python virtual environment for CDK
cd cdk
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "📦 Installing CDK dependencies..."
source .venv/bin/activate
pip install -q -r requirements.txt

# Bootstrap CDK if needed (will skip if already bootstrapped)
echo "🔧 Checking CDK bootstrap..."
cdk bootstrap 2>/dev/null || true

# Deploy
echo "🚢 Deploying stack..."
cdk deploy --require-approval never

echo ""
echo "✅ Deployment complete!"
echo ""
echo "To view logs:"
echo "  aws logs tail /aws/ecs/claude-proxy --follow"
echo ""
echo "To update the service (after code changes):"
echo "  ./deploy-fargate.sh"
echo ""
