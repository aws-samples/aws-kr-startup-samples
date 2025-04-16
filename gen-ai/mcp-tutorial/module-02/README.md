# Module-02: MCP 서버 배포 및 Claude Desktop 연결 설정

이 모듈에서는 MCP(Model Context Protocol) 서버를 AWS CDK를 사용하여 AWS 환경에 배포하고, Claude Desktop 애플리케이션과 연결하는 방법을 안내합니다.

## SSE Transport 방식 소개

SSE(Server-Sent Events) Transport는 MCP 서버와 클라이언트 간의 통신 방식 중 하나로, 다음과 같은 특징이 있습니다:

- **로컬 또는 원격 실행**: SSE Transport는 로컬 환경이나 원격 서버에서 모두 실행 가능합니다.
- **사용자 관리**: 사용자가 직접 서버를 관리하고 운영합니다.
- **네트워크 통신**: 네트워크를 통해 클라이언트와 서버 간 통신이 이루어집니다.
- **여러 기기 공유**: 하나의 MCP 서버를 여러 기기에서 공유하여 사용할 수 있습니다.
- **외부 연결**: Claude Desktop과 같은 클라이언트는 MCP 서버의 `/sse` 엔드포인트 URL을 통해 연결합니다.

이 방식을 사용하면 중앙 집중식 MCP 서버를 구축하여 여러 사용자나 애플리케이션에서 공유할 수 있으며, 서버 측에서 추가적인 로직이나 보안 계층을 구현할 수 있습니다.

## MCP-Server-CDK 스택 개요

MCP-Server-CDK 스택은 다음과 같은 AWS 리소스를 생성합니다:

- **VPC**: MCP 서버를 위한 네트워크 환경을 제공합니다.
- **ECS 클러스터**: EC2 인스턴스 기반의 컨테이너 실행 환경을 제공합니다.
- **EC2 인스턴스**: ARM 기반 c6g.xlarge 인스턴스를 사용하여 MCP 서버를 호스팅합니다.
- **Application Load Balancer(ALB)**: MCP 서버로의 트래픽을 분산하고 HTTP 엔드포인트를 제공합니다.
- **ECS 서비스 및 작업 정의**: MCP 서버 컨테이너를 실행하기 위한 설정을 제공합니다.
- **CloudWatch Logs**: 서버 로그를 저장하고 모니터링합니다.

이 스택은 컨테이너화된 MCP 서버를 EC2 인스턴스에서 실행하여 확장성과 안정성을 제공합니다.

## 배포 단계

### 1. MCP-Server-CDK 스택 배포

1. 프로젝트 디렉토리로 이동합니다:
   ```bash
   cd mcp-server-cdk
   ```

2. 가상 환경 활성화:
   ```bash
   source .venv/bin/activate  # Linux/Mac
   source.bat                # Windows
   ```

3. 필요한 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```

4. CDK 배포:
   ```bash
   cdk deploy
   ```

5. 배포가 완료되면 출력에서 ALB URL을 확인하고 기록해 둡니다. 이 URL은 Claude Desktop 설정에 필요합니다.
   ```
   Outputs:
   McpServerAmazonECSStack.McpServerAmazonECSStackALBHostnameOutput = McpServerAmazonECSStack-xxxxxxxxxxxx.your-region.elb.amazonaws.com
   ```

### 2. MCP-Remote 설치

MCP-Remote는 Claude Desktop과 MCP 서버 간의 통신을 관리하는 도구입니다.

1. MCP-Remote를 설치합니다:
   ```bash
   npm install -g mcp-remote
   ```

2. 설치가 완료되었는지 확인합니다:
   ```bash
   mcp-remote --version
   ```

### 3. Claude Desktop 설정

1. Claude Desktop 애플리케이션을 실행합니다.

2. 설정(Settings) 메뉴로 이동합니다.

3. "Developer" 섹션을 찾습니다.

4. "Edit Config"를 통해 claude_desktop_config.json을 찾습니다.

5. claude_desktop_config.json 파일에 아래처럼 설정을 추가합니다.

```
{
  "mcpServers": {
    "weather": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "<YOUR-ALB-ENDPOINT>/sse",
        "--allow-http"
      ]
    }
  }
}
```

6. 설정을 저장하고, Claude Desktop을 재실행합니다.

### 4. 연결 테스트

1. Claude Desktop에서 새 대화를 시작합니다.

2. `What’s the weather in Sacramento?` 와 같은 질문을 입력하여 응답이 MCP 서버를 통해 처리되는지 확인합니다.

3. 응답이 정상적으로 오면 설정이 완료된 것입니다.
