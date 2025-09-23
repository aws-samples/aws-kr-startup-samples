#!/bin/bash

# Strands Agent AWS Batch 배포 스크립트

set -e

echo "🚀 Strands Agent AWS Batch 배포를 시작합니다..."

# 가상환경 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Python 가상환경이 활성화되지 않았습니다."
    echo "다음 명령어로 가상환경을 활성화하세요:"
    echo "python3 -m venv .venv && source .venv/bin/activate"
    exit 1
fi

# 의존성 설치
echo "📦 의존성을 설치합니다..."
pip install -r requirements.txt

# CDK 부트스트랩 확인
echo "🔧 CDK 부트스트랩을 확인합니다..."
if ! cdk bootstrap --show-template > /dev/null 2>&1; then
    echo "CDK 부트스트랩을 실행합니다..."
    cdk bootstrap
fi

# CDK 배포
echo "☁️  AWS 리소스를 배포합니다..."
cdk deploy --require-approval never

echo "✅ 배포가 완료되었습니다!"
echo ""
echo "📋 다음 명령어로 배포된 리소스를 확인할 수 있습니다:"
echo "aws batch describe-job-queues"
echo "aws s3 ls | grep strands-agent-data"
echo ""
echo "🔍 로그 확인:"
echo "aws logs describe-log-groups --log-group-name-prefix '/aws/batch/strands-agent'"