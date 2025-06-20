다른 언어로 읽기: [English](./README.md), Korean(한국어)

# MCP 서버 CDK 배포

이 프로젝트는 AWS CDK를 사용하여 Model Context Protocol (MCP) 날씨 서버를 AWS에 배포합니다. 인프라는 Application Load Balancer가 포함된 EC2 기반 ECS를 포함하며, 스트리밍 HTTP 전송을 통한 MCP 서버의 확장 가능하고 프로덕션 준비가 완료된 배포를 제공합니다.

## 아키텍처 개요

CDK 스택은 MCP 서버 호스팅을 위한 완전한 AWS 인프라를 생성합니다:

```
                    인터넷
                       │
                       ▼
              ┌─────────────────┐
              │ Application     │
              │ Load Balancer   │
              │   (포트 80)      │
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   ECS 클러스터   │
              │                 │
              │  ┌─────────────┐│
              │  │ ECS 서비스   ││
              │  │             ││
              │  │ ┌─────────┐ ││
              │  │ │MCP 서버 │ ││
              │  │ │FastMCP  │ ││
              │  │ │포트 8000│ ││
              │  │ │         │ ││
              │  │ │날씨     │ ││
              │  │ │ 도구    │ ││
              │  │ └─────────┘ ││
              │  └─────────────┘│
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ National Weather│
              │  Service API    │
              │ (weather.gov)   │
              └─────────────────┘
```

## AWS 인프라 구성 요소

### 네트워크 계층
- **VPC**: 고가용성을 위한 2개 가용 영역을 가진 사용자 정의 VPC
- **서브넷**: ALB용 퍼블릭 서브넷, ECS 태스크용 프라이빗 서브넷
- **NAT 게이트웨이**: 프라이빗 서브넷에서 아웃바운드 인터넷 액세스를 위한 단일 NAT 게이트웨이
- **인터넷 게이트웨이**: 퍼블릭 인터넷 액세스를 위해 VPC에 연결

### 컴퓨팅 계층
- **ECS 클러스터**: 관리형 컨테이너 오케스트레이션 서비스
- **EC2 인스턴스**: 비용 효율적인 성능을 위한 ARM 기반 c6g.xlarge 인스턴스
- **오토 스케일링 그룹**: 1개 인스턴스의 원하는 용량 유지
- **태스크 정의**: 컨테이너 사양 및 리소스 할당 정의

### 로드 밸런싱
- **Application Load Balancer (ALB)**: ECS 태스크 간 들어오는 트래픽 분산
- **타겟 그룹**: 포트 8000에서 정상적인 ECS 태스크로 트래픽 라우팅
- **헬스 체크**: 5초마다 `/health` 엔드포인트 모니터링
- **리스너**: 포트 80에서 HTTP 트래픽 수신

### 보안
- **보안 그룹**: 포트 80에서 HTTP 트래픽을 허용하도록 구성
- **IAM 역할**: ECS 태스크 및 서비스에 대한 최소 권한 액세스
- **VPC 격리**: 프라이빗 서브넷이 컨테이너 워크로드 보호

## 프로젝트 구조

```
mcp-server/
├── app/                                  # MCP 서버 애플리케이션
│   ├── main.py                           # FastMCP 날씨 서버 구현
│   ├── pyproject.toml                    # Python 프로젝트 설정
│   ├── Dockerfile                        # 컨테이너 이미지 정의
│   ├── uv.lock                           # 의존성 잠금 파일
│   └── .gitignore                        # Git 무시 패턴
├── stacks/                               # CDK 인프라 코드
│   ├── __init__.py                       # Python 패키지 초기화
│   └── mcp_server_amazon_ecs_stack.py    # 메인 CDK 스택 정의
├── app.py                                # CDK 애플리케이션 진입점
├── cdk.json                              # CDK 설정
├── requirements.txt                      # CDK 의존성
├── source.bat                            # Windows 환경 설정
└── README.md                             # 이 문서
```

## MCP 서버 애플리케이션

컨테이너화된 애플리케이션은 MCP 도구를 통해 날씨 데이터를 제공합니다:

### 사용 가능한 도구
- **get_alerts**: 미국 주의 활성 날씨 경보 조회
- **get_forecast**: 좌표에 대한 상세 날씨 예보 제공

### 설정
- **전송**: 포트 8000에서 스트리밍 HTTP
- **API 통합**: National Weather Service (NWS) API
- **헬스 체크**: 로드 밸런서 모니터링을 위한 `/health` 엔드포인트

## 사전 요구 사항

- 적절한 자격 증명으로 구성된 AWS CLI
- Node.js 18+ 및 npm
- Python 3.9+
- AWS CDK CLI 설치 (`npm install -g aws-cdk`)

## 설치 및 배포

### 1. 환경 설정

저장소를 복제하고 프로젝트 디렉터리로 이동:
```bash
cd module-02/mcp-server
```

### 2. 의존성 설치

CDK 의존성 설치:
```bash
pip install -r requirements.txt
```

### 3. CDK 부트스트랩 (최초 1회만)

CDK를 위한 AWS 환경 부트스트랩:
```bash
cdk bootstrap aws://ACCOUNT-NUMBER/REGION
```

### 4. 인프라 배포

스택 배포:
```bash
cdk deploy
```

### 5. 배포 확인

배포 후 다음을 포함한 출력을 받게 됩니다:
- MCP 서버 액세스를 위한 ALB DNS 이름
- ECS 서비스 이름
- ECS 클러스터 이름

## 설정

### 인스턴스 설정
- **인스턴스 타입**: c6g.xlarge (ARM 기반)
- **원하는 용량**: 1개 인스턴스
- **메모리 제한**: 태스크당 4096 MiB
- **CPU**: 태스크당 2048 CPU 단위

### 로드 밸런서 설정
- **프로토콜**: HTTP
- **포트**: 80 (외부), 8000 (컨테이너)
- **헬스 체크 경로**: `/health`
- **헬스 체크 간격**: 5초

### 네트워크 설정
- **VPC CIDR**: 자동 할당
- **가용 영역**: 2개
- **NAT 게이트웨이**: 1개 (비용 최적화)

## 모니터링 및 로깅

### CloudWatch 통합
- **컨테이너 로그**: CloudWatch Logs로 자동 전송
- **로그 그룹**: `/aws/ecs/McpServerAmazonECSStack`
- **메트릭**: CloudWatch에서 ECS 서비스 및 ALB 메트릭 사용 가능

### 헬스 모니터링
- **ALB 헬스 체크**: 컨테이너 상태 지속적 모니터링
- **자동 복구**: 비정상 태스크 자동 교체
- **CloudWatch 알람**: 자동 알림 설정 가능

## 스케일링 설정

### 현재 설정
- **원하는 용량**: 1개 태스크
- **인스턴스 수**: 1개 EC2 인스턴스

### 스케일링 옵션
용량을 늘리려면 스택을 수정:
```python
# mcp_server_amazon_ecs_stack.py에서
desired_count=2,  # 태스크 수 증가
desired_capacity=2,  # EC2 인스턴스 수 증가
```

## 비용 최적화

### 현재 설정
- **인스턴스 타입**: c6g.xlarge (비용 효율성을 위한 ARM 기반)
- **NAT 게이트웨이**: AZ 간 공유되는 단일 NAT 게이트웨이
- **로드 밸런서**: 애플리케이션용 단일 ALB

### 예상 월별 비용
- EC2 인스턴스 (c6g.xlarge): 월 ~$140
- Application Load Balancer: 월 ~$20
- NAT 게이트웨이: 월 ~$45
- 데이터 전송: 사용량에 따라 가변

## MCP 클라이언트 연결

배포 후 ALB DNS 이름을 사용하여 MCP 클라이언트 연결:

```json
{
  "mcpServers": {
    "weather": {
      "command": "http",
      "args": ["http://YOUR-ALB-DNS-NAME"]
    }
  }
}
```

## 문제 해결

### 일반적인 문제

1. **배포 실패**
   - AWS 자격 증명 및 권한 확인
   - CDK 부트스트랩 상태 확인
   - 컨테이너 빌드를 위한 Docker 실행 확인

2. **헬스 체크 실패**
   - 컨테이너가 성공적으로 시작되는지 확인
   - 애플리케이션 오류에 대한 CloudWatch 로그 확인
   - 헬스 엔드포인트가 200 상태를 반환하는지 확인

3. **연결 문제**
   - 보안 그룹 규칙이 포트 80을 허용하는지 확인
   - ALB 타겟 그룹 상태 확인
   - 태스크가 프라이빗 서브넷에서 실행되고 있는지 확인

### 유용한 명령어

```bash
# 스택 상태 확인
cdk diff

# CloudFormation 이벤트 보기
aws cloudformation describe-stack-events --stack-name McpServerAmazonECSStack

# ECS 서비스 상태 확인
aws ecs describe-services --cluster CLUSTER-NAME --services SERVICE-NAME

# 컨테이너 로그 보기
aws logs tail /aws/ecs/McpServerAmazonECSStack --follow
```

## 정리

지속적인 비용을 피하기 위해 더 이상 필요하지 않을 때 스택을 제거:

```bash
cdk destroy
```

이렇게 하면 스택에서 생성된 모든 AWS 리소스가 제거됩니다.

## 보안 고려 사항

- **네트워크 격리**: ECS 태스크는 프라이빗 서브넷에서 실행
- **최소 권한**: IAM 역할은 최소 권한 원칙을 따름
- **HTTPS**: ALB 레벨에서 SSL/TLS 종료 추가 고려
- **VPC 엔드포인트**: NAT 비용 절감을 위해 AWS 서비스용 VPC 엔드포인트 추가 고려

## 추가 사용자 정의

스택은 추가 기능으로 확장할 수 있습니다:
- **자동 스케일링**: 메트릭 기반 ECS 서비스 자동 스케일링 구성
- **HTTPS**: SSL 인증서 및 HTTPS 리스너 추가
- **사용자 정의 도메인**: 사용자 정의 도메인 이름을 위한 Route 53 통합
- **모니터링**: 향상된 CloudWatch 대시보드 및 알람
- **시크릿 관리**: 민감한 데이터를 위한 AWS Secrets Manager 통합