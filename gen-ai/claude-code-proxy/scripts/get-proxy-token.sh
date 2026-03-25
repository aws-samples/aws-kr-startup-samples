#!/bin/bash
# get-proxy-token.sh — apiKeyHelper for Claude Code
#
# SSO 자격증명으로 프록시의 /auth/sso 엔드포인트를 호출하여
# access_key를 발급받아 반환합니다.
#
# 사용법:
#   1. ~/.claude/settings.json에 apiKeyHelper로 등록
#   2. aws sso login 수행
#   3. claude 실행 → 이 스크립트가 자동 호출됨
#
# 환경변수:
#   PROXY_TOKEN_SERVICE_URL (필수): API Gateway /auth/sso 엔드포인트 URL
#   AWS_PROFILE (선택): SSO 프로필명
#   AWS_REGION (선택, 기본: us-east-1): API Gateway 리전

set -euo pipefail

TOKEN_SERVICE_URL="${PROXY_TOKEN_SERVICE_URL:?PROXY_TOKEN_SERVICE_URL is required}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# 1. SSO 자격증명 export
eval $(aws configure export-credentials --format env 2>/dev/null) || {
  echo "ERROR: aws sso login required" >&2
  exit 1
}

# 2. API Gateway /auth/sso 호출 (SigV4 서명)
RESPONSE=$(curl -s -X POST "$TOKEN_SERVICE_URL" \
  --aws-sigv4 "aws:amz:${AWS_REGION}:execute-api" \
  --user "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}" \
  -H "x-amz-security-token: ${AWS_SESSION_TOKEN:-}" \
  -H "Content-Type: application/json" \
  -d '{}' 2>/dev/null)

# 3. access_key 추출 및 반환
ACCESS_KEY=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_key',''))" 2>/dev/null)

if [ -z "$ACCESS_KEY" ]; then
  echo "ERROR: Failed to get access_key: $RESPONSE" >&2
  exit 1
fi

echo "$ACCESS_KEY"
