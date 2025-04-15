# MCP Server CDK Project

이 프로젝트는 ECS EC2에 Python 애플리케이션을 배포하고 ALB를 연결하는 CDK 스택을 포함하고 있습니다.

## 프로젝트 구조

```
mcp-server-cdk/
├── app/                    # Python 애플리케이션 코드
│   ├── app.py              # FastAPI 애플리케이션
│   ├── requirements.txt    # 애플리케이션 의존성
│   └── Dockerfile          # 컨테이너 이미지 빌드 파일
├── stacks/                 # CDK 스택 코드
│   └── mcp_server_amazon_ecs_stack.py  # ECS, ALB 인프라 정의
├── app.py                  # CDK 앱 진입점
├── cdk.json               # CDK 설정 파일
├── requirements.txt       # CDK 의존성
└── source.bat            # Windows 환경 설정 스크립트
```

## 배포 방법

1. 가상 환경 활성화:
```
$ source .venv/bin/activate  # Linux/Mac
$ source.bat                # Windows
```

2. 필요한 의존성 설치:
```
$ pip install -r requirements.txt
```

3. CDK 배포:
```
$ cdk deploy
```

## 인프라 구성 요소

- VPC: 2개의 가용 영역과 1개의 NAT 게이트웨이
- ECS 클러스터: EC2 기반 서비스 실행을 위한 클러스터
- EC2 인스턴스: ARM 기반 c6g.xlarge 인스턴스 사용
- ECS 서비스: 1개의 태스크로 구성된 서비스
- Application Load Balancer: 인터넷 트래픽을 서비스로 라우팅
- 보안 그룹: HTTP(80) 트래픽 허용

## 애플리케이션

FastAPI 애플리케이션으로 다음 엔드포인트를 제공합니다:
- `/`: 기본 인사 메시지 반환
- `/health`: 헬스 체크 엔드포인트 (5초 간격으로 체크)

## 참고사항

- EC2 태스크는 메모리 및 CPU 제한 파라미터를 지원하지 않습니다.
- 컨테이너는 8000 포트에서 실행됩니다.
- ALB는 80 포트로 HTTP 트래픽을 수신합니다.
