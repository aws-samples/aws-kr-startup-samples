# Strands Agent with EventBridge & Fargate

AWS EventBridge와 Fargate를 사용하여 Strands Agent를 주기적으로 실행하는 서버리스 템플릿입니다.

## 목적

- **주기적 실행**: EventBridge 스케줄러를 통해 정해진 시간에 자동으로 Strands Agent 실행
- **서버리스**: Fargate를 사용하여 서버 관리 없이 컨테이너 기반 실행
- **확장성**: 필요에 따라 스케줄 및 실행 환경을 쉽게 조정 가능
- **비용 효율성**: 실행 시에만 리소스 사용

## 아키텍처

```
EventBridge Scheduler → ECS Fargate Task → S3 (결과 저장)
```

- **EventBridge**: 스케줄 기반 트리거
- **ECS Fargate**: 컨테이너 실행 환경
- **S3**: 실행 결과 및 로그 저장
- **VPC**: 네트워크 격리 및 보안

## 실행 방법

### 1. 사전 요구사항

```bash
# AWS CLI 설정
aws configure

# CDK 설치
npm install -g aws-cdk

# Python 의존성 설치
pip install -r requirements.txt
```

### 2. 배포

```bash
# CDK 부트스트랩 (최초 1회)
cdk bootstrap

# 스택 배포
cdk deploy
```

### 3. 스케줄 설정

배포 후 EventBridge 콘솔에서 스케줄을 조정할 수 있습니다:
- 기본값: 매일 오전 9시 (UTC)
- 수정 가능: cron 표현식 또는 rate 표현식 사용

### 4. 모니터링

- **CloudWatch Logs**: ECS 태스크 실행 로그
- **S3**: 실행 결과 JSON 파일
- **EventBridge**: 스케줄 실행 이력

## 설정 변경

### 스케줄 변경
`strands_agent_with_eventbridge_fargate_stack.py`에서 EventBridge 규칙 수정:

```python
# 매시간 실행
schedule=events.Schedule.rate(Duration.hours(1))

# 특정 시간 실행 (매일 오후 2시)
schedule=events.Schedule.cron(hour="14", minute="0")
```

### Agent 로직 변경
`docker/src/main.py`에서 실제 Strands Agent 로직 구현

### 환경 변수 추가
스택에서 ECS 태스크 정의에 환경 변수 추가 가능

## 정리

```bash
# 스택 삭제
cdk destroy

# 또는 스크립트 사용
./scripts/cleanup.sh
```

## 비용 최적화

- Fargate Spot 사용 고려
- 실행 빈도 조정
- S3 Lifecycle 정책 설정
- CloudWatch 로그 보존 기간 설정

## 보안

- VPC 내 프라이빗 서브넷에서 실행
- IAM 역할 기반 최소 권한 원칙
- S3 버킷 암호화 적용
- 네트워크 ACL 및 보안 그룹 설정
