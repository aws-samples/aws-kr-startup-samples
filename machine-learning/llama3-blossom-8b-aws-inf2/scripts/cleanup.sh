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
