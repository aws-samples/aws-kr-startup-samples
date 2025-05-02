# MCP 서버 배포 및 Claude Desktop 연결 설정

## 개요
이 모듈에서는 MCP(Model Context Protocol) 서버를 AWS CDK를 사용하여 AWS 환경에 배포하고, Claude Desktop 애플리케이션과 연결하는 방법을 학습합니다. 중앙 집중식 MCP 서버를 구축하여 여러 사용자나 애플리케이션에서 공유할 수 있는 환경을 구성합니다.

## 주요 개념

### MCP Transport 방식
MCP(Model Context Protocol)는 LLM과 외부 도구 간의 통신을 위해 다양한 Transport 방식을 지원합니다. MCP 사양(2025-03-26)에 따르면 다음과 같은 Transport 방식이 있습니다:

#### 1. stdio Transport
- **실행 방식**: 표준 입출력(stdin/stdout)을 통한 통신
- **사용 환경**: 로컬 환경에서 주로 사용
- **특징**: 클라이언트가 서버 프로세스를 직접 시작하고 관리
- **장점**: 설정이 간단하고 추가 네트워크 구성이 필요 없음
- **사용 사례**: 로컬 개발 환경, 단일 사용자 시나리오

#### 2. Streamable HTTP Transport
- **실행 방식**: HTTP POST와 GET을 통한 양방향 통신
- **특징**:
  - 단일 엔드포인트에서 POST와 GET을 모두 지원
  - Server-Sent Events (SSE)를 통한 스트리밍 지원
  - 세션 관리 기능 제공
- **장점**:
  - 확장성 있는 서버-클라이언트 통신
  - 세션 기반 상태 관리
  - 연결 재개 및 메시지 재전송 지원
- **사용 사례**: 클라우드 환경, 다중 사용자 시나리오

#### 3. HTTP+SSE Transport (2024-11-05 버전)
- **실행 방식**: HTTP를 통한 단방향 이벤트 스트림
- **엔드포인트**: `/sse`
- **특징**: 서버에서 클라이언트로의 지속적인 데이터 스트림 제공
- **장점**: 표준 HTTP를 사용하여 방화벽 통과가 용이함
- **사용 사례**: 중앙 집중식 서버, 여러 사용자가 공유하는 환경
- **호환성**: 2025-03-26 버전과의 하위 호환성 유지

### 이번 모듈에서 HTTP+SSE Transport를 선택한 이유

이 모듈에서는 2024-11-05 버전의 HTTP+SSE Transport 방식을 사용합니다. 이는 다음과 같은 이유 때문입니다:

1. **간단한 구현**: Streamable HTTP Transport에 비해 구현이 더 간단합니다.
2. **하위 호환성**: 2025-03-26 버전과의 하위 호환성이 보장되어 있습니다.
3. **튜토리얼 목적**: 이 모듈의 목적은 MCP의 기본 개념과 클라우드 배포를 이해하는 것이므로, 더 간단한 Transport 방식을 선택했습니다.

향후 프로덕션 환경에서는 2025-03-26 버전의 Streamable HTTP Transport를 사용하는 것을 고려해볼 수 있습니다. 이는 세션 관리, 연결 재개, 메시지 재전송과 같은 고급 기능을 제공하기 때문입니다.

### MCP-Server-CDK 스택

MCP-Server-CDK 스택은 다음과 같은 AWS 리소스를 생성합니다:

- **VPC**: MCP 서버를 위한 네트워크 환경을 제공합니다.
- **ECS 클러스터**: EC2 인스턴스 기반의 컨테이너 실행 환경을 제공합니다.
- **EC2 인스턴스**: ARM 기반 c6g.xlarge 인스턴스를 사용하여 MCP 서버를 호스팅합니다.
- **Application Load Balancer(ALB)**: MCP 서버로의 트래픽을 분산하고 HTTP 엔드포인트를 제공합니다.
- **ECS 서비스 및 작업 정의**: MCP 서버 컨테이너를 실행하기 위한 설정을 제공합니다.
- **CloudWatch Logs**: 서버 로그를 저장하고 모니터링합니다.

## 사전 준비사항

- AWS 계정 및 적절한 권한
- AWS CDK 설치
- Node.js 및 npm 설치

## 실습 가이드

### 실습 1: MCP-Server-CDK 스택 배포

1. 프로젝트 디렉토리로 이동합니다:
   ```bash
   cd mcp-server-cdk
   ```

2. 가상 환경을 활성화합니다:
   ```bash
   source .venv/bin/activate  # Linux/Mac
   source.bat                 # Windows
   ```

3. 필요한 의존성을 설치합니다:
   ```bash
   pip install -r requirements.txt
   ```

4. CDK를 배포합니다:
   ```bash
   cdk deploy
   ```

5. 배포가 완료되면 출력에서 ALB URL을 확인하고 기록해 둡니다:
   ```
   Outputs:
   McpServerAmazonECSStack.McpServerAmazonECSStackALBHostnameOutput = McpServerAmazonECSStack-xxxxxxxxxxxx.your-region.elb.amazonaws.com
   ```
   > 💡 **팁**: 이 URL은 다음 단계에서 Claude Desktop 설정에 필요합니다.

### 실습 2: MCP-Remote 설치 (Claude Desktop 환경)

mcp-remote는 Claude Desktop이 설치된 로컬 환경에 설치합니다.

1. MCP-Remote를 설치합니다:
   ```bash
   npm install -g mcp-remote
   ```

2. 설치가 완료되었는지 확인합니다:
   ```bash
   which mcp-remote
   ```
   > 💡 **참고**: MCP-Remote는 Claude Desktop과 MCP 서버 간의 통신을 관리하는 도구입니다.

### 실습 3: Claude Desktop 설정

1. Claude Desktop 애플리케이션을 실행합니다.

2. 설정(Settings) 메뉴로 이동합니다.

3. "Developer" 섹션을 찾습니다.

4. "Edit Config"를 통해 claude_desktop_config.json을 찾습니다.

5. claude_desktop_config.json 파일에 아래처럼 설정을 추가합니다:
   ```json
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

### 실습 4: 연결 테스트

1. Claude Desktop에서 새 대화를 시작합니다.

2. `What are the active weather alerts in Texas?` 와 같은 질문을 입력하여 응답을 확인합니다.

3. 응답이 정상적으로 오면 설정이 완료된 것입니다.

## 요약
이 모듈에서는 AWS CDK를 사용하여 MCP 서버를 AWS 환경에 배포하고, Claude Desktop과 연결하는 방법을 학습했습니다. 여러 MCP Transport 방식 중 HTTP+SSE Transport를 선택하여 중앙 집중식 MCP 서버를 구축했습니다. 이 방식은 여러 사용자가 공유할 수 있는 확장성 있는 환경을 제공하며, 클라우드 환경에 쉽게 배포할 수 있는 장점이 있습니다. 이를 통해 확장성과 안정성을 갖춘 MCP 서버 인프라를 구축할 수 있습니다.

## 참고 자료
- [Model Context Protocol 공식 문서](https://modelcontextprotocol.io/)
- [MCP Transport 사양](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [AWS CDK 문서](https://docs.aws.amazon.com/cdk/latest/guide/home.html)
- [MCP-Remote GitHub 저장소](https://github.com/anthropic-labs/mcp-remote)