# Claude Code Proxy - Project Steering

이 문서는 Claude Code Proxy 프로젝트의 아키텍처, 컨벤션, 개발 가이드라인을 정의합니다.

## 프로젝트 개요

Anthropic API를 프록시하고, rate limit(429) 발생 시 자동으로 AWS Bedrock으로 폴백하는 ECS Fargate 서비스입니다.

### 핵심 기능
- Anthropic API 프록시 (Claude 모델 지원)
- 429 rate limit 시 자동 Bedrock 폴백
- DynamoDB 기반 사용량 추적 및 rate limit 상태 관리
- 멀티유저 지원 (path parameter 기반)
- 웹 대시보드 (`/ui`)

## 프로젝트 구조

```
claude-code-proxy/
├── app/                          # FastAPI 애플리케이션
│   ├── main.py                   # 앱 진입점, 미들웨어, 예외 핸들러
│   ├── config.py                 # 환경변수 설정
│   ├── models.py                 # Pydantic 모델 정의
│   ├── utils.py                  # 유틸리티 함수 (track_usage)
│   ├── routes/
│   │   ├── messages.py           # /v1/messages 프록시 엔드포인트
│   │   ├── usage.py              # /v1/usage 사용량 조회 API
│   │   └── ui.py                 # /ui 대시보드
│   ├── Dockerfile
│   └── requirements.txt
├── cdk/                          # AWS CDK 인프라
│   ├── app.py                    # CDK 앱 진입점
│   ├── claude_proxy_fargate_stack.py  # Fargate 스택 정의
│   └── requirements.txt
└── README.md
```

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 헬스체크 |
| `/v1/messages` | POST | Anthropic Messages API 프록시 (기본 유저) |
| `/user/{user_id}/v1/messages` | POST | 멀티유저 Messages API 프록시 |
| `/v1/usage/me` | GET | 개인 사용량 조회 |
| `/v1/usage` | GET | 전체 사용자 사용량 조회 |
| `/ui` | GET | 사용량 대시보드 |
| `/debug/env` | GET | 환경변수 디버그 |

## DynamoDB 스키마

### Rate Limit 테이블 (`claude-proxy-rate-limits`)
| 속성 | 타입 | 설명 |
|------|------|------|
| `user_id` (PK) | String | 사용자 식별자 |
| `retry_until` | Number | rate limit 해제 시간 (Unix timestamp) |
| `retry_after_seconds` | Number | 원본 retry-after 값 |
| `ttl` | Number | 자동 만료 시간 |
| `created_at` | Number | 생성 시간 |

### Usage 테이블 (`claude-proxy-usage`)
| 속성 | 타입 | 설명 |
|------|------|------|
| `user_period` (PK) | String | `{user_id}#{YYYY-MM-DD}` 형식 |
| `input_tokens` | Number | 입력 토큰 수 (atomic counter) |
| `output_tokens` | Number | 출력 토큰 수 (atomic counter) |
| `total_tokens` | Number | 총 토큰 수 |
| `request_count` | Number | 요청 횟수 |
| `model` | String | 사용 모델명 |
| `request_type` | String | `bedrock` (현재 Bedrock만 추적) |
| `period_type` | String | `daily` |
| `ttl` | Number | 90일 후 자동 만료 |

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `BEDROCK_FALLBACK_ENABLED` | `true` | Bedrock 폴백 활성화 |
| `RATE_LIMIT_TRACKING_ENABLED` | `true` | Rate limit 추적 활성화 |
| `RATE_LIMIT_TABLE_NAME` | `claude-proxy-rate-limits` | Rate limit DynamoDB 테이블 |
| `USAGE_TRACKING_ENABLED` | `true` | 사용량 추적 활성화 |
| `USAGE_TABLE_NAME` | `claude-proxy-usage` | Usage DynamoDB 테이블 |
| `RETRY_THRESHOLD_SECONDS` | `30` | 재시도 임계값 |
| `MAX_RETRY_WAIT_SECONDS` | `10` | 최대 대기 시간 |
| `AWS_REGION` | `us-east-1` | AWS 리전 |
| `FORCE_RATE_LIMIT` | `false` | 테스트용 강제 rate limit |

## 코딩 컨벤션

### Python
- Python 3.12+ 사용
- FastAPI 프레임워크
- Pydantic v2 모델 사용
- async/await 패턴 사용
- 로깅: `logging` 모듈, 이모지 prefix로 로그 구분
  - `📥` 요청 수신
  - `🔄` 폴백 시도
  - `✅` 성공
  - `❌` 에러
  - `📊` 사용량/통계

### 에러 처리
- HTTPException으로 API 에러 반환
- Anthropic API 에러 형식 유지: `{"type": "error", "error": {...}}`
- 모든 예외는 로깅 후 적절한 HTTP 상태 코드 반환

### DynamoDB 패턴
- Atomic counter 사용 (`if_not_exists` + `ADD`)
- TTL 기반 자동 만료
- PAY_PER_REQUEST 과금 모드

## 인프라 (CDK)

### 아키텍처
```
Internet → ALB (Public) → Fargate (Private) → NAT Gateway → Internet
                                            → DynamoDB
                                            → Bedrock
```

### 주요 리소스
- VPC: 2 AZ, Public/Private 서브넷
- NAT Gateway: 1개 (비용 최적화)
- ECS Fargate: 0.5 vCPU, 1GB 메모리
- ALB: Public 서브넷에 배치
- DynamoDB: PAY_PER_REQUEST, TTL 활성화

### CDK 배포
```bash
cd cdk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap
cdk deploy
```

## 인증 방식

### 지원하는 인증
1. `x-api-key` 헤더: Anthropic API 키
2. `Authorization: Bearer` 헤더: Claude Pro 구독 토큰
3. 환경변수: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`

### 사용자 식별
- 메시지 호출: `/user/{user_id}/v1/messages` path parameter
- 사용량 조회: `claude-code-user` query parameter
- 기본값: `default`

## 폴백 로직

1. Anthropic API 호출
2. 429 응답 시:
   - `retry-after` 헤더 확인
   - DynamoDB에 rate limit 상태 저장
   - Bedrock으로 폴백
3. 다음 요청:
   - DynamoDB에서 rate limit 상태 확인
   - 아직 제한 중이면 바로 Bedrock 사용

## 테스트

### 로컬 실행
```bash
cd app
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

### 폴백 테스트
```bash
export FORCE_RATE_LIMIT=true
# 요청 시 강제로 Bedrock 폴백 발생
```

## 주의사항

- Anthropic API 사용량은 추적하지 않음 (Bedrock 폴백만 추적)
- 사용자 인증 없음 (API 키는 클라이언트가 직접 전달)
- DynamoDB Scan 사용 시 대량 데이터에서 성능 저하 가능
- 비용 계산은 Bedrock Claude Haiku 4.5 기준
