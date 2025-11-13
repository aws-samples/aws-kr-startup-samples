# Claude Code Proxy with Bedrock Fallback

Anthropic API를 프록시하고, rate limit 발생 시 자동으로 AWS Bedrock으로 폴백하는 Lambda Function URL 서비스입니다.

## 🎯 주요 기능

- ✅ **Anthropic API 프록시**: Claude 3.5 Sonnet, Haiku 등 모든 모델 지원
- 🔄 **자동 Bedrock 폴백**: 429 rate limit 시 자동으로 AWS Bedrock으로 전환
- 💾 **멀티유저 rate limit 추적**: DynamoDB 기반 사용자별 rate limit 상태 추적
- ⚡ **Lambda Function URL**: 서버리스로 빠르고 간단한 배포
- 🔐 **API 키 플로우스루**: 클라이언트가 자신의 Anthropic API 키를 헤더로 전달

```
Client (Claude Code)
       ↓ (x-api-key header)
   Lambda Function URL
       ↓
   Anthropic API ----[429 error]---→ Bedrock
       ↓
   DynamoDB (rate limiting)
```

## 🚀 빠른 배포 (2분)

```bash
# 1. Docker 이미지 빌드
cd app
docker build --platform linux/arm64 -t claude-proxy:latest .

# 2. AWS 배포
cd ..
chmod +x deploy.sh
./deploy.sh
```

**끝!** 🎉 배포 완료되면 Function URL이 출력됩니다.

## 💻 로컬 실행

```bash
cd app
pip install -r requirements.txt
python main.py
```

## 📖 사용법

```bash
curl -X POST "https://YOUR-FUNCTION-URL.lambda-url.us-east-1.on.aws/v1/messages?claude-code-user=USERNAME" \
  -H "x-api-key: sk-ant-..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Claude Code에서 사용

`.claude/settings.json`:
```json
{
  "apiConfiguration": {
    "baseURL": "https://YOUR-FUNCTION-URL.lambda-url.us-east-1.on.aws?claude-code-user=alice"
  }
}
```

## 🔄 Bedrock 폴백 동작

1. **Anthropic API 호출** → 정상 응답 반환
2. **429 rate limit 발생**:
   - `retry-after` 헤더 확인
   - 30초 이하면 잠시 대기 후 재시도
   - 30초 초과면 즉시 Bedrock으로 폴백
   - DynamoDB에 rate limit 상태 저장 (TTL 자동 만료)
3. **다음 요청**: DynamoDB에서 rate limit 확인, 아직 제한 중이면 바로 Bedrock 사용

## 👥 멀티유저 지원

`claude-code-user` 쿼리 파라미터로 유저 식별:

```bash
# Alice의 요청
curl "...?claude-code-user=alice" ...

# Bob의 요청
curl "...?claude-code-user=bob" ...
```

각 유저별로 독립적인 rate limit이 추적됩니다.

## ⚙️ 환경변수 (Lambda)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `RATE_LIMIT_TRACKING_ENABLED` | `true` | Rate limit 추적 활성화 |
| `BEDROCK_FALLBACK_ENABLED` | `true` | Bedrock fallback 활성화 |
| `RETRY_THRESHOLD_SECONDS` | `30` | 재시도 임계값 (초) |
| `MAX_RETRY_WAIT_SECONDS` | `10` | 최대 대기 시간 (초) |
| `RATE_LIMIT_TABLE_NAME` | `claude-proxy-rate-limits` | DynamoDB 테이블 이름 |

**참고**: Anthropic API 키는 클라이언트 요청 헤더(`x-api-key`)로 전달됩니다.

## 📁 프로젝트 구조

```
claude-code-proxy/
├── app/
│   ├── main.py              # FastAPI 애플리케이션
│   ├── requirements.txt     # Python 의존성
│   └── Dockerfile           # Lambda 컨테이너 이미지
├── deploy.sh                # AWS 배포 스크립트
└── README.md
```

## 🔧 관리 작업

### Lambda 함수 업데이트

```bash
# 코드 변경 후
cd app
docker build --platform linux/arm64 -t claude-proxy:latest .
cd ..
./deploy.sh
```

### 환경변수 변경

```bash
aws lambda update-function-configuration \
  --function-name claude-proxy-api \
  --environment Variables='{
    RATE_LIMIT_TRACKING_ENABLED=false,
    BEDROCK_FALLBACK_ENABLED=true,
    RETRY_THRESHOLD_SECONDS=60
  }'
```

### 로그 확인

```bash
aws logs tail /aws/lambda/claude-proxy-api --follow
```

### DynamoDB 테이블 확인

```bash
aws dynamodb scan --table-name claude-proxy-rate-limits
```

## 🧹 삭제

```bash
# Lambda 함수 삭제
aws lambda delete-function --function-name claude-proxy-api

# DynamoDB 테이블 삭제
aws dynamodb delete-table --table-name claude-proxy-rate-limits

# ECR 저장소 삭제
aws ecr delete-repository --repository-name claude-proxy --force

# IAM Role 삭제
aws iam detach-role-policy \
  --role-name claude-proxy-api-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role-policy --role-name claude-proxy-api-role --policy-name BedrockAndDynamoDB
aws iam delete-role --role-name claude-proxy-api-role
```

## 📝 라이선스

MIT

## 🤝 기여

Issues와 Pull Requests를 환영합니다!
