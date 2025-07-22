# MCP Server Proxy Application

이 디렉토리는 MCP (Model Context Protocol) 서버의 프록시 애플리케이션을 포함합니다.

## 프로젝트 구조

```
mcp-server-proxy/
├── app/                    # MCP Proxy 애플리케이션
│   ├── proxy_server.py     # FastAPI 기반 프록시 서버
│   ├── mcp.json            # MCP 설정 파일
│   ├── pyproject.toml      # Python 프로젝트 설정
│   ├── uv.lock             # uv 의존성
│   ├── Dockerfile          # Docker 이미지 빌드 파일
│   └── .python-version     # Python 버전 지정
│
├── iac/                    # Infrastructure as Code (CDK)
│   ├── app.py              # CDK 앱 진입점
│   ├── cdk/                # CDK 스택 정의
│   │   ├── __init__.py
│   │   └── mcp_proxy_stack.py
│   ├── cdk.json            # CDK 설정 파일
│   └── requirements.txt    # CDK Python 의존성
│   
└── README.md               # 메인 프로젝트 README
```

## 애플리케이션 구성 요소

## 배포

이 애플리케이션은 AWS ECS Fargate에 배포됩니다. CDK를 사용하여 인프라를 관리합니다.

### 사전 요구사항

1. **AWS CLI 설정**
   ```bash
   aws configure
   ```

2. **AWS CDK 설치**
   ```bash
   npm install -g aws-cdk
   ```

3. **Docker 설치 및 실행**
   - Docker Desktop이 설치되어 있고 실행 중이어야 합니다.

### 배포 단계

#### 1. **./app/mcp.json** 수정
- MCP 서버 설정 파일 수정 (아래 예시)

```json
{
  "mcpServers": {
    "aws-api-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-api-mcp-server@latest"
      ],
      "env": {
        "AWS_REGION": "ap-northeast-2"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

#### 2. CDK 환경 설정

```bash
# iac 디렉토리로 이동
cd iac

# Python 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# CDK 의존성 설치
pip install -r requirements.txt
```

#### 3. CDK Bootstrap (최초 1회만)

```bash
# AWS 계정에 CDK Bootstrap 실행
cdk bootstrap
```

#### 4. 인프라 배포

```bash
# CDK 스택 배포
cdk deploy

# 배포 전 변경사항 미리보기 (선택사항)
cdk diff
```

#### 5. 배포 확인

배포가 완료되면 다음 정보가 출력됩니다:
- ALB DNS 이름
- ECS 서비스 정보
- CloudWatch 로그 그룹

`McpProxyStack.ServiceURL` 를 remote mcp server 주소로 활용하세요.

```bash
# 헬스체크 확인
curl http://<ALB_DNS_NAME>/health

# MCP 서버 
http://<ALB_DNS_NAME>/mcp
```

### 배포 관리

#### 스택 업데이트
```bash
cd iac
cdk deploy
```

#### 스택 삭제
```bash
cd iac
cdk destroy
```

## 주의 사항

- 현재 python 기반의 MCP 서버만 지원합니다.

