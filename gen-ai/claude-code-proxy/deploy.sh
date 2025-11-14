#!/bin/bash
set -e

# 설정
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="claude-proxy"
FUNCTION_NAME="claude-proxy-api"
TABLE_NAME="claude-proxy-rate-limits"

echo "🚀 Deploying Claude Proxy to AWS Lambda..."

# 1. ECR 저장소 생성 (이미 있으면 무시)
echo "📦 Creating ECR repository..."
aws ecr create-repository --repository-name $ECR_REPO --region $REGION 2>/dev/null || echo "   ECR repository already exists"

# 2. Docker 이미지 빌드
echo "🔨 Building Docker image..."
cd app
docker build --platform linux/arm64 --provenance=false -t claude-proxy:latest .
cd ..

# 3. ECR 로그인
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# 4. Docker 이미지 태그 & 푸시
echo "🐳 Pushing Docker image..."
IMAGE_URI=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO:latest
docker tag claude-proxy:latest $IMAGE_URI
docker push $IMAGE_URI

# 5. DynamoDB 테이블 생성 (이미 있으면 무시)
echo "💾 Creating DynamoDB table..."
aws dynamodb create-table \
  --table-name $TABLE_NAME \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION 2>/dev/null || echo "   DynamoDB table already exists"

# 6. IAM Role 생성 (이미 있으면 무시)
echo "🔑 Creating IAM role..."
ROLE_NAME="${FUNCTION_NAME}-role"
aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null || echo "   IAM role already exists"

aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true

aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name BedrockAndDynamoDB \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ],
        "Resource": "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/'$TABLE_NAME'"
      }
    ]
  }' 2>/dev/null || true

# IAM Role이 전파될 때까지 대기
echo "⏳ Waiting for IAM role to propagate..."
sleep 10

# 7. Lambda 함수 생성 또는 업데이트
echo "⚡ Creating/updating Lambda function..."
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"

if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
  # 업데이트
  aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --image-uri $IMAGE_URI \
    --region $REGION
  
  aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --timeout 600 \
    --memory-size 1024 \
    --environment Variables="{
      AWS_LWA_INVOKE_MODE=response_stream,
      AWS_LWA_PORT=8082,
      AWS_LWA_READINESS_CHECK_PATH=/health,
      RATE_LIMIT_TABLE_NAME=$TABLE_NAME,
      RATE_LIMIT_TRACKING_ENABLED=true,
      BEDROCK_FALLBACK_ENABLED=true,
      RETRY_THRESHOLD_SECONDS=30,
      MAX_RETRY_WAIT_SECONDS=10
    }" \
    --region $REGION
else
  # 생성
  aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --package-type Image \
    --code ImageUri=$IMAGE_URI \
    --role $ROLE_ARN \
    --timeout 600 \
    --memory-size 1024 \
    --architectures arm64 \
    --environment Variables="{
      AWS_LWA_INVOKE_MODE=response_stream,
      AWS_LWA_PORT=8082,
      AWS_LWA_READINESS_CHECK_PATH=/health,
      RATE_LIMIT_TABLE_NAME=$TABLE_NAME,
      RATE_LIMIT_TRACKING_ENABLED=true,
      BEDROCK_FALLBACK_ENABLED=true,
      RETRY_THRESHOLD_SECONDS=30,
      MAX_RETRY_WAIT_SECONDS=10
    }" \
    --region $REGION
fi

# 8. Function URL 생성 (이미 있으면 무시)
echo "🌐 Creating Function URL..."
aws lambda create-function-url-config \
  --function-name $FUNCTION_NAME \
  --auth-type NONE \
  --invoke-mode RESPONSE_STREAM \
  --region $REGION 2>/dev/null || echo "   Function URL already exists"

aws lambda add-permission \
  --function-name $FUNCTION_NAME \
  --statement-id FunctionURLAllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE \
  --region $REGION 2>/dev/null || true

# 9. Function URL 출력
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📍 Function URL:"
aws lambda get-function-url-config \
  --function-name $FUNCTION_NAME \
  --region $REGION \
  --query 'FunctionUrl' \
  --output text

echo ""
echo "💡 Usage:"
echo 'curl -X POST "$(YOUR_FUNCTION_URL)/v1/messages?claude-code-user=USERNAME" \'
echo '  -H "x-api-key: YOUR-ANTHROPIC-API-KEY" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"model":"claude-3-5-sonnet-20241022","max_tokens":1024,"messages":[{"role":"user","content":"Hello"}]}'"'"
