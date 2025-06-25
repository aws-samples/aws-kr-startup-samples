# MCP 서버 배포 및 Claude Desktop 연결 설정

## 개요
이 모듈에서는 MCP(Model Context Protocol) 서버를 AWS CDK를 사용하여 AWS 환경에 배포하고, Claude Desktop 애플리케이션과 연결하는 방법을 학습합니다. 레거시 SSE 전송과 최신 Streamable HTTP 전송 구현을 모두 포함하여 여러 사용자나 애플리케이션에서 공유할 수 있는 중앙 집중식 MCP 서버를 구축합니다.

## 주요 개념

### MCP Transport 방식
MCP(Model Context Protocol)는 LLM과 외부 도구 간의 통신을 위해 다양한 Transport 방식을 지원합니다. MCP 사양(2025-03-26)에 따르면 다음과 같은 Transport 방식이 있습니다:

#### 1. stdio Transport
- **실행 방식**: 표준 입출력(stdin/stdout)을 통한 통신
- **사용 환경**: 로컬 환경에서 주로 사용
- **특징**: 클라이언트가 서버 프로세스를 직접 시작하고 관리
- **장점**: 설정이 간단하고 추가 네트워크 구성이 필요 없음
- **사용 사례**: 로컬 개발 환경, 단일 사용자 시나리오

#### 2. Streamable HTTP Transport (2025-03-26) ⭐ **현재 표준**
- **실행 방식**: 단일 엔드포인트를 통한 HTTP 양방향 통신
- **특징**:
  - 단일 엔드포인트(`/mcp`)에서 모든 MCP 통신 처리
  - JSON 응답과 SSE 스트리밍 모두 지원
  - 무상태 운영을 통한 고급 세션 관리
  - 내장된 오류 복구 및 메시지 재전송
- **장점**:
  - 확장성 있는 서버-클라이언트 통신
  - 클라우드 배포에 최적화
  - 향상된 성능과 안정성
  - 미래 지향적 설계
- **사용 사례**: 프로덕션 환경, 클라우드 배포, 다중 사용자 시나리오

#### 3. HTTP+SSE Transport (2024-11-05) ⚠️ **레거시**
- **실행 방식**: HTTP를 통한 단방향 이벤트 스트림
- **엔드포인트**: 별도의 `/sse` 및 `/messages` 엔드포인트
- **특징**: 서버에서 클라이언트로의 지속적인 데이터 스트림 제공
- **장점**: 간단한 구현, 방화벽 친화적
- **사용 사례**: 교육 목적, 하위 호환성
- **상태**: deprecated, 호환성을 위해 유지

## 사전 준비사항

- AWS 계정 및 적절한 권한
- AWS CDK 설치
- Node.js 및 npm 설치
- Python 3.11 이상

## 빠른 시작 가이드

### 옵션 1: 최신 구현 (권장)

1. **최신 구현으로 이동**:
   ```bash
   cd mcp-server
   ```

2. **설정 및 배포**:
   ```bash
   # CDK 환경 설정
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate.bat  # Windows
   
   # 의존성 설치
   pip install -r requirements.txt
   
   # AWS 배포
   cdk bootstrap  # 처음만
   cdk deploy
   ```

3. **로컬 개발**:
   ```bash
   cd app
   pip install -e .
   cd src
   python server.py
   ```

### 옵션 2: 레거시 구현 (호환성용)

1. **레거시 구현으로 이동**:
   ```bash
   cd mcp-server-cdk
   ```

2. **기존 배포 프로세스 따르기**:
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   cdk deploy
   ```

## Claude Desktop 설정

### 최신 구현용 (Streamable HTTP)

1. **MCP 클라이언트 도구 설치**:
   ```bash
   npm install -g @anthropic/mcp-client
   ```

2. **claude_desktop_config.json 설정**:
   ```json
   {
     "mcpServers": {
       "weather": {
         "command": "mcp-client",
         "args": [
           "http://<YOUR-ALB-ENDPOINT>/mcp",
           "--transport", "streamable-http"
         ]
       }
     }
   }
   ```

### 레거시 구현용 (SSE)

1. **MCP-Remote 설치**:
   ```bash
   npm install -g mcp-remote
   ```

2. **claude_desktop_config.json 설정**:
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

## 연결 테스트

1. Claude Desktop에서 새 대화 시작
2. 질문하기: `What are the active weather alerts in Texas?`
3. MCP 서버가 올바르게 응답하는지 확인

## 아키텍처 비교

### 최신 구현 (`mcp-server/`)
```
Client → HTTP POST /mcp → StreamableHTTPSessionManager → MCP Server → Weather API
```

### 레거시 구현 (`mcp-server-cdk/`)
```
Client → SSE /sse + POST /messages → SSE Transport → MCP Server → Weather API
```

## 레거시에서 최신으로 마이그레이션

현재 레거시 SSE 구현을 사용 중인 경우 마이그레이션 방법:

1. **새 구현을 기존 구현과 함께 배포**
2. **클라이언트 설정을 Streamable HTTP transport로 업데이트**
3. **기존 워크플로우로 철저히 테스트**
4. **기존 구현에서 새 구현으로 트래픽 점진적 전환**
5. **마이그레이션 완료 후 레거시 구현 해제**

## 문제 해결

### 일반적인 문제

1. **포트 충돌**: `PORT` 환경 변수 변경
2. **Transport 불일치**: 클라이언트와 서버가 동일한 transport 프로토콜 사용 확인
3. **네트워크 연결**: ALB 엔드포인트 접근성 확인
4. **의존성**: 일관된 Python 의존성을 위해 `uv sync` 사용

### 디버깅 팁

- 서버 측 문제는 CloudWatch 로그 확인
- HTTP 요청 검사는 브라우저 개발자 도구 사용
- MCP 클라이언트 설정 구문 확인
- 기본 연결은 curl로 테스트

## 성능 고려사항

### 최신 구현의 이점
- **낮은 지연 시간**: 대부분의 작업에서 단일 HTTP 라운드트립
- **향상된 확장성**: 무상태 설계로 수평 확장 지원
- **효율적인 리소스 사용**: 연결 오버헤드 감소
- **오류 복구**: 내장된 재시도 및 복구 메커니즘

### 레거시 구현의 제한사항
- **다중 연결**: 별도의 SSE 및 HTTP 연결 필요
- **상태 관리**: 더 복잡한 세션 처리
- **리소스 오버헤드**: 높은 메모리 및 연결 사용량

## 요약

이 모듈은 레거시 SSE transport에서 최신 Streamable HTTP transport까지 MCP 서버 배포 패턴의 진화를 보여줍니다. `mcp-server/`의 최신 구현은 프로덕션 MCP 서버 배포의 현재 모범 사례를 나타내며, `mcp-server-cdk/`의 레거시 구현은 하위 호환성과 교육적 가치를 제공합니다.

새 프로젝트에는 최신 구현을 선택하고, 향상된 성능, 확장성, 미래 호환성을 활용하기 위해 기존 배포의 마이그레이션을 고려하세요.

## 참고 자료

- [Model Context Protocol 공식 문서](https://modelcontextprotocol.io/)
- [MCP Streamable HTTP Transport 사양](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http)
- [AWS CDK 문서](https://docs.aws.amazon.com/cdk/latest/guide/home.html)
- [MCP 클라이언트 도구](https://github.com/anthropics/mcp-client)