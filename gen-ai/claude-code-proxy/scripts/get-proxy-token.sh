#!/bin/bash
# get-proxy-token.sh — apiKeyHelper for Claude Code
#
# SSO 자격증명으로 프록시의 /auth/sso 엔드포인트를 호출하여
# access_key를 발급받아 반환합니다.
# 로컬 캐시를 사용하여 TTL 내에는 재호출 없이 캐시된 키를 반환합니다.
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
CACHE_FILE="$HOME/.claude/.proxy-token-cache"

# 1. 캐시 확인
if [ -f "$CACHE_FILE" ]; then
  EXPIRES_AT=$(python3 -c "
import json, sys
from datetime import datetime, timezone
try:
    data = json.load(open('$CACHE_FILE'))
    exp = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    # 만료 5분 전까지 유효
    if (exp - now).total_seconds() > 300:
        print(data['access_key'])
except Exception:
    pass
" 2>/dev/null)
  if [ -n "$EXPIRES_AT" ]; then
    echo "$EXPIRES_AT"
    exit 0
  fi
fi

# 2. SSO 자격증명 export
eval $(aws configure export-credentials --format env 2>/dev/null) || {
  echo "ERROR: aws sso login required" >&2
  exit 1
}

# 3. Caller ARN 조회
CALLER_ARN=$(aws sts get-caller-identity --query Arn --output text 2>/dev/null) || {
  echo "ERROR: Failed to get caller identity" >&2
  exit 1
}

# 4. API Gateway /auth/sso 호출 (SigV4 서명)
RESPONSE=$(curl -s -X POST "$TOKEN_SERVICE_URL" \
  --aws-sigv4 "aws:amz:${AWS_REGION}:execute-api" \
  --user "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}" \
  -H "x-amz-security-token: ${AWS_SESSION_TOKEN:-}" \
  -H "x-sso-arn: ${CALLER_ARN}" \
  -H "Content-Type: application/json" \
  -d '{}' 2>/dev/null)

# 5. access_key 추출
ACCESS_KEY=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_key',''))" 2>/dev/null)

if [ -z "$ACCESS_KEY" ]; then
  echo "ERROR: Failed to get access_key: $RESPONSE" >&2
  exit 1
fi

# 6. 캐시 저장
mkdir -p "$(dirname "$CACHE_FILE")"
echo "$RESPONSE" > "$CACHE_FILE"
chmod 600 "$CACHE_FILE"

echo "$ACCESS_KEY"
