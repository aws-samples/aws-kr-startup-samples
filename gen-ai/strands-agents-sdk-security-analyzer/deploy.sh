#!/bin/bash

# AWS Lambda 보안 분석기 배포 스크립트

set -e  # 에러 발생시 스크립트 중단

echo "🚀 AWS Lambda 보안 분석기 배포를 시작합니다..."

# 1. packaging 디렉터리 초기화
echo "📦 패키징 디렉터리 준비 중..."
rm -rf packaging/_dependencies
mkdir -p packaging/_dependencies

# 2. 시스템 아키텍처 확인
ARCH=$(uname -m)
echo "현재 시스템 아키텍처: $ARCH"

# 3. Lambda 의존성 설치
echo "📥 Lambda 의존성 설치 중..."

if [[ "$ARCH" == "arm64" ]]; then
    echo "Apple Silicon 감지 - Docker를 사용한 크로스 플랫폼 빌드"
    
    # Docker가 설치되어 있는지 확인
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker가 설치되어 있지 않습니다."
        echo "Docker Desktop을 설치하거나 다음 명령어를 사용하세요:"
        echo "brew install --cask docker"
        exit 1
    fi
    
    # Docker를 사용한 크로스 플랫폼 빌드
    docker run --rm --platform linux/amd64 \
        -v "$(pwd)":/workspace \
        -w /workspace \
        python:3.12-slim \
        bash -c "
            pip install -r lambda/requirements.txt \
                --target packaging/_dependencies \
                --no-build-isolation \
                --force-reinstall \
                --quiet
        "
else
    echo "x86_64 시스템 - 직접 빌드"
    pip install -r lambda/requirements.txt \
        --target packaging/_dependencies \
        --platform linux_x86_64 \
        --only-binary=:all: \
        --no-build-isolation \
        --force-reinstall \
        --quiet
fi

# 4. Lambda 패키징
echo "📦 Lambda 함수 패키징 중..."
python package_for_lambda.py

# 5. CDK 배포
echo "🚀 CDK 배포 중..."
cdk deploy --require-approval never

echo "✅ 배포가 완료되었습니다!"
echo ""
echo "Lambda 함수명: AWSSecurityAgentFunction"
echo "AWS 콘솔에서 확인하세요: https://console.aws.amazon.com/lambda/"
echo ""
echo "테스트 실행:"
echo "aws lambda invoke --function-name AWSSecurityAgentFunction --region us-east-1 --invocation-type Event --payload '{}' response.json"