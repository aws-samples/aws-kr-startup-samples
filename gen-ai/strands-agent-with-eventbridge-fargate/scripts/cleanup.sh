#!/bin/bash

# Strands Agent AWS Batch 정리 스크립트

set -e

echo "🧹 Strands Agent AWS Batch 리소스를 정리합니다..."

# 실행 중인 작업 확인
echo "📋 실행 중인 Batch 작업을 확인합니다..."
RUNNING_JOBS=$(aws batch list-jobs --job-queue StrandsAgentBatchStack-StrandsAgentJobQueue --job-status RUNNING --query 'jobList[].jobId' --output text 2>/dev/null || echo "")

if [[ -n "$RUNNING_JOBS" ]]; then
    echo "⚠️  실행 중인 작업이 있습니다. 작업을 취소합니다..."
    for job_id in $RUNNING_JOBS; do
        echo "작업 취소: $job_id"
        aws batch cancel-job --job-id "$job_id" --reason "Cleanup script execution"
    done
    
    echo "⏳ 작업 취소를 기다립니다..."
    sleep 30
fi

# CDK 스택 삭제
echo "☁️  AWS 리소스를 삭제합니다..."
cdk destroy --force

echo "✅ 정리가 완료되었습니다!"
echo ""
echo "🔍 다음 명령어로 리소스가 완전히 삭제되었는지 확인하세요:"
echo "aws batch describe-compute-environments"
echo "aws s3 ls | grep strands-agent-data"