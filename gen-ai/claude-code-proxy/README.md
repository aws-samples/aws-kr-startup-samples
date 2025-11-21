# Claude Code Proxy with Bedrock Fallback

Anthropic API를 프록시하고, rate limit 발생 시 자동으로 AWS Bedrock으로 폴백하는 ECS Fargate 서비스입니다.

## 주요 기능

- **Anthropic API 프록시**: Claude 4.5 Sonnet, Haiku 등 모든 모델 지원
- **자동 Bedrock 폴백**: 429 rate limit 시 자동으로 AWS Bedrock으로 전환
- **멀티유저 rate limit 추적**: DynamoDB 기반 사용자별 rate limit 상태 추적
- **ECS Fargate**: 안정적이고 확장 가능한 컨테이너 기반 배포
- **API 키 플로우스루**: 클라이언트가 자신의 Anthropic API 키를 헤더로 전달
- **ALB 기반**: Application Load Balancer로 고가용성 보장

```
Client (Claude Code)
       ↓ (x-api-key header)
   ALB → ECS Fargate
       ↓
   Anthropic API ----[429 error]---→ Bedrock
       ↓
   DynamoDB (rate limiting)
```

## 배포

### 사전 요구사항

- AWS CLI 설정 완료
- Docker 설치
- Python 3.12+

### 배포
```bash
# Public ECR 403 에러 방지
docker logout public.ecr.aws

# CDK CLI 설치
pip install aws-cdk-lib

# Python 환경 설정
cd cdk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Bootstrap & 배포
cdk bootstrap
cdk deploy
```

배포 완료되면 ALB URL이 출력됩니다.

## 로컬 실행

```bash
cd app
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

## 사용법

### 기본 API 호출

```bash
curl -X POST "http://YOUR-ALB-DNS/user/USERNAME/v1/messages" \
  -H "x-api-key: sk-ant-..." \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Claude Code에서 사용

**설정 파일:** `~/.config/cline/anthropic-settings.json` 또는 `.claude/settings.local.json`

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://YOUR-ALB-DNS/user/USERNAME"
  }
}
```

또는:

```json
{
  "anthropicBaseURL": "http://YOUR-ALB-DNS/user/USERNAME"
}
```

Claude Code가 자동으로 `/v1/messages`를 붙여서 최종 URL이 됩니다:
```
http://YOUR-ALB-DNS/user/USERNAME/v1/messages
```

## Bedrock 폴백 동작

1. **Anthropic API 호출** → 정상 응답 반환
2. **429 rate limit 발생**:
   - `retry-after` 헤더 확인
   - 30초 이하면 잠시 대기 후 재시도
   - 30초 초과면 즉시 Bedrock으로 폴백
   - DynamoDB에 rate limit 상태 저장 (TTL 자동 만료)
3. **다음 요청**: DynamoDB에서 rate limit 확인, 아직 제한 중이면 바로 Bedrock 사용

## 멀티유저 지원

Path parameter로 유저 식별:

```bash
# Alice의 요청
curl "http://YOUR-ALB-DNS/user/alice/v1/messages" ...

# Bob의 요청
curl "http://YOUR-ALB-DNS/user/bob/v1/messages" ...
```

각 유저별로 독립적인 rate limit이 추적됩니다.

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `RATE_LIMIT_TRACKING_ENABLED` | `true` | Rate limit 추적 활성화 |
| `BEDROCK_FALLBACK_ENABLED` | `true` | Bedrock fallback 활성화 |
| `RETRY_THRESHOLD_SECONDS` | `30` | 재시도 임계값 (초) |
| `MAX_RETRY_WAIT_SECONDS` | `10` | 최대 대기 시간 (초) |
| `RATE_LIMIT_TABLE_NAME` | `claude-proxy-rate-limits` | DynamoDB 테이블 이름 |


## 프로젝트 구조

```
claude-code-proxy/
├── app/
│   ├── main.py              # FastAPI 애플리케이션
│   ├── requirements.txt     # Python 의존성
│   └── Dockerfile           # Fargate 컨테이너 이미지
├── cdk/
│   ├── app.py              # CDK 앱 진입점
│   ├── claude_proxy_fargate_stack.py  # Fargate 스택 정의
│   ├── requirements.txt    # CDK 의존성
│   └── cdk.json           # CDK 설정
└── README.md
```

## 운영 가이드

### 로그 확인

```bash
aws logs tail /aws/ecs/claude-proxy --region us-east-1 --follow
```

### 환경변수 변경

`cdk/claude_proxy_fargate_stack.py` 수정 후 재배포:

```python
environment={
    "RETRY_THRESHOLD_SECONDS": "60",  # 변경
    ...
}
```

```bash
cd cdk && cdk deploy
```

### 스케일링

**수평 확장:**
```python
desired_count=3,
```

**수직 확장:**
```python
cpu=1024,
memory_limit_mib=2048,
```

### 모니터링

```bash
curl http://YOUR-ALB-DNS/health
aws dynamodb scan --table-name claude-proxy-rate-limits --region us-east-1
```

## 테스트

```bash
curl -X POST "http://YOUR-ALB-DNS/user/test/v1/messages" \
  -H "x-api-key: sk-ant-..." \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":50,"messages":[{"role":"user","content":"Hi"}]}'
```

## 리소스 삭제

```bash
cd cdk
source .venv/bin/activate
cdk destroy
```

**삭제되는 리소스:**
- ECS Fargate Service & Cluster
- Application Load Balancer
- VPC, Subnets, Security Groups
- IAM Roles
- CloudWatch Log Groups

**DynamoDB 테이블 수동 삭제:**
```bash
aws dynamodb delete-table --table-name claude-proxy-rate-limits --region us-east-1
```

## 비용 예상

| 리소스 | 월 예상 비용 |
|--------|-------------|
| ECS Fargate (0.5 vCPU, 1GB) | ~$15 |
| Application Load Balancer | ~$16 |
| DynamoDB (PAY_PER_REQUEST) | 무료 티어 |
| CloudWatch Logs (1주일 보관) | ~$1 |
| 데이터 전송 | 사용량 기반 |
| **총합** | **~$32/월** |

## 보안

- ALB가 모든 외부 트래픽 수신
- Fargate 태스크는 Security Group으로 ALB에서만 접근 가능
- API 키는 클라이언트에서 직접 전달 (서버 저장 안 함)
- DynamoDB는 VPC 내부에서만 접근
- IAM Role 기반 최소 권한 원칙

## 트러블슈팅

### 배포 실패

```bash
aws cloudformation describe-stack-events \
  --stack-name ClaudeProxyFargateStack --region us-east-1
```

### 서비스가 시작 안 됨

```bash
aws ecs describe-tasks --cluster <CLUSTER> --tasks <TASK_ARN> --region us-east-1
aws ecs list-tasks --cluster <CLUSTER> --desired-status STOPPED --region us-east-1
```

### ALB Health Check 실패

```bash
aws elbv2 describe-target-health --target-group-arn <ARN> --region us-east-1
```

## 라이선스

MIT

## 기여

Issues와 Pull Requests를 환영합니다!

