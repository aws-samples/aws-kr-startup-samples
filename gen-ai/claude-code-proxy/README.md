# Claude Code Proxy with Bedrock Fallback

Anthropic API를 프록시하고, rate limit 발생 시 자동으로 AWS Bedrock으로 폴백하는 ECS Fargate 서비스입니다.

## 🎯 주요 기능

- ✅ **Anthropic API 프록시**: Claude 3.5 Sonnet, Haiku 등 모든 모델 지원
- 🔄 **자동 Bedrock 폴백**: 429 rate limit 시 자동으로 AWS Bedrock으로 전환
- 💾 **멀티유저 rate limit 추적**: DynamoDB 기반 사용자별 rate limit 상태 추적
- ⚡ **ECS Fargate**: 안정적이고 확장 가능한 컨테이너 기반 배포
- 🔐 **API 키 플로우스루**: 클라이언트가 자신의 Anthropic API 키를 헤더로 전달
- 🌐 **ALB 기반**: Application Load Balancer로 고가용성 보장

```
Client (Claude Code)
       ↓ (x-api-key header)
   ALB → ECS Fargate
       ↓
   Anthropic API ----[429 error]---→ Bedrock
       ↓
   DynamoDB (rate limiting)
```

## 🚀 빠른 배포 (5분)

### 사전 요구사항

- AWS CLI 설정 완료
- Docker 설치
- Node.js (CDK CLI용)
- Python 3.12+

### 배포

```bash
# 1. CDK CLI 설치 (한 번만)
npm install -g aws-cdk

# 2. Python 환경 설정
cd cdk
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. CDK Bootstrap (첫 배포 시 한 번만)
cdk bootstrap

# 4. 배포
cdk deploy
```

**끝!** 🎉 배포 완료되면 ALB URL이 출력됩니다.

> **참고**: `cdk deploy`는 Docker 이미지 빌드부터 ECR 업로드, 인프라 배포까지 자동으로 처리합니다.

## 💻 로컬 실행

```bash
cd app
pip install -r requirements.txt

# 환경변수 설정 (선택)
export RATE_LIMIT_TRACKING_ENABLED=false
export BEDROCK_FALLBACK_ENABLED=true

# 실행
uvicorn main:app --host 0.0.0.0 --port 8080
```

## 📖 사용법

### 기본 API 호출

```bash
# Path-based user identification (권장)
curl -X POST "http://YOUR-ALB-DNS/user/USERNAME/v1/messages" \
  -H "x-api-key: sk-ant-..." \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# 또는 기본 경로 (user_id = "default")
curl -X POST "http://YOUR-ALB-DNS/v1/messages" \
  -H "x-api-key: sk-ant-..." \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{...}'
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

## 🔄 Bedrock 폴백 동작

1. **Anthropic API 호출** → 정상 응답 반환
2. **429 rate limit 발생**:
   - `retry-after` 헤더 확인
   - 30초 이하면 잠시 대기 후 재시도
   - 30초 초과면 즉시 Bedrock으로 폴백
   - DynamoDB에 rate limit 상태 저장 (TTL 자동 만료)
3. **다음 요청**: DynamoDB에서 rate limit 확인, 아직 제한 중이면 바로 Bedrock 사용

## 👥 멀티유저 지원

Path parameter로 유저 식별:

```bash
# Alice의 요청
curl "http://YOUR-ALB-DNS/user/alice/v1/messages" ...

# Bob의 요청
curl "http://YOUR-ALB-DNS/user/bob/v1/messages" ...
```

각 유저별로 독립적인 rate limit이 추적됩니다.

## ⚙️ 환경변수

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
│   └── Dockerfile           # Fargate 컨테이너 이미지
├── cdk/
│   ├── app.py              # CDK 앱 진입점
│   ├── claude_proxy_fargate_stack.py  # Fargate 스택 정의
│   ├── requirements.txt    # CDK 의존성
│   └── cdk.json           # CDK 설정
├── test-proxy.sh          # 테스트 스크립트
└── README.md
```

## 🔧 운영 가이드

### 로그 확인

```bash
# 로그 그룹 찾기
aws logs describe-log-groups --region us-east-1 \
  --query 'logGroups[?contains(logGroupName, `ClaudeProxy`)].logGroupName'

# 실시간 로그
aws logs tail <LOG_GROUP_NAME> --region us-east-1 --follow
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

**수평 확장** (태스크 수 증가):

```python
# cdk/claude_proxy_fargate_stack.py
desired_count=3,  # 1 → 3
```

**수직 확장** (리소스 증가):

```python
cpu=1024,  # 0.5 → 1 vCPU
memory_limit_mib=2048,  # 1GB → 2GB
```

### 모니터링

```bash
# Health check
curl http://YOUR-ALB-DNS/health

# DynamoDB 확인
aws dynamodb scan --table-name claude-proxy-rate-limits --region us-east-1

# ECS 서비스 상태
aws ecs describe-services \
  --cluster $(aws ecs list-clusters --region us-east-1 --query 'clusterArns[?contains(@, `ClaudeProxy`)]' --output text) \
  --services $(aws ecs list-services --cluster <CLUSTER_ARN> --region us-east-1 --query 'serviceArns[0]' --output text) \
  --region us-east-1
```

## 🧪 테스트

```bash
# 테스트 스크립트 사용
ANTHROPIC_API_KEY='sk-ant-...' ./test-proxy.sh

# 또는 직접 curl
export ANTHROPIC_API_KEY='sk-ant-...'
curl -X POST "http://YOUR-ALB-DNS/user/test/v1/messages" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":50,"messages":[{"role":"user","content":"Hi"}]}'
```

## 🧹 리소스 삭제

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

**수동 삭제 필요:**
```bash
# DynamoDB 테이블 (데이터 보호를 위해 자동 삭제 안 됨)
aws dynamodb delete-table --table-name claude-proxy-rate-limits --region us-east-1
```

## 💰 비용 예상

| 리소스 | 월 예상 비용 |
|--------|-------------|
| ECS Fargate (0.5 vCPU, 1GB) | ~$15 |
| Application Load Balancer | ~$16 |
| DynamoDB (PAY_PER_REQUEST) | 무료 티어 |
| CloudWatch Logs (1주일 보관) | ~$1 |
| 데이터 전송 | 사용량 기반 |
| **총합** | **~$32/월** |

## 🔒 보안

- ✅ ALB가 모든 외부 트래픽 수신
- ✅ Fargate 태스크는 Security Group으로 ALB에서만 접근 가능
- ✅ API 키는 클라이언트에서 직접 전달 (서버 저장 안 함)
- ✅ DynamoDB는 VPC 내부에서만 접근
- ✅ IAM Role 기반 최소 권한 원칙

## 🐛 트러블슈팅

### 배포 실패

```bash
# CloudFormation 이벤트 확인
aws cloudformation describe-stack-events \
  --stack-name ClaudeProxyFargateStack \
  --region us-east-1 --max-items 20
```

### 서비스가 시작 안 됨

```bash
# ECS 태스크 로그 확인
aws ecs describe-tasks --cluster <CLUSTER> --tasks <TASK_ARN> --region us-east-1

# 중지된 태스크 확인
aws ecs list-tasks --cluster <CLUSTER> --desired-status STOPPED --region us-east-1
```

### ALB Health Check 실패

```bash
# Target Group 상태 확인
aws elbv2 describe-target-health --target-group-arn <ARN> --region us-east-1

# Security Group 확인
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=*ClaudeProxy*" --region us-east-1
```

## 📝 라이선스

MIT

## 🤝 기여

Issues와 Pull Requests를 환영합니다!

