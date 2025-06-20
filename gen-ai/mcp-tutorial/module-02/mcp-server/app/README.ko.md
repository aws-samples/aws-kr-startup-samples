다른 언어로 읽기: [English](./README.md), Korean(한국어)

# MCP 날씨 서버

National Weather Service (NWS) API를 통해 날씨 데이터를 제공하는 Model Context Protocol (MCP) 서버입니다. 이 프로젝트는 컨테이너화와 스트리밍 HTTP 전송을 사용하여 MCP 서버를 AWS에 배포하는 방법을 보여줍니다.

## 개요

이 MCP 서버는 날씨 관련 도구를 구현하며 AWS 인프라에 배포되도록 설계되었습니다. 스트리밍 HTTP 인터페이스를 통해 미국 내 위치에 대한 실시간 날씨 경보와 예보를 제공합니다.

## 프로젝트 구조

```
mcp-server/
├── main.py          # MCP 서버 구현
├── pyproject.toml   # 프로젝트 설정 및 의존성
├── Dockerfile       # AWS 배포용 컨테이너 설정
├── uv.lock         # 의존성 잠금 파일
└── README.md       # 이 문서
```

## 기능

- **날씨 경보**: 미국 모든 주의 활성 날씨 경보 조회
- **날씨 예보**: 특정 좌표에 대한 상세 날씨 예보 제공
- **스트리밍 HTTP**: 안정적인 MCP 통신을 위한 HTTP 기반 전송
- **AWS 준비**: AWS 서비스에 쉽게 배포할 수 있도록 컨테이너화
- **FastMCP 프레임워크**: 최신 FastMCP 프레임워크를 사용하여 구축

## MCP 도구

### 1. get_alerts
지정된 미국 주의 활성 날씨 경보를 조회합니다.

**매개변수:**
- `state` (문자열): 미국 주 코드 2자리 (예: "CA", "NY", "TX")

**반환값:** 이벤트 유형, 지역, 심각도, 지침을 포함한 형식화된 날씨 경보

### 2. get_forecast
특정 좌표에 대한 상세 날씨 예보를 조회합니다.

**매개변수:**
- `latitude` (실수): 위치의 위도
- `longitude` (실수): 위치의 경도

**반환값:** 온도, 바람, 상세 설명이 포함된 5일 날씨 예보

## 로컬 개발

### 사전 요구사항

- Python 3.12 이상
- uv 패키지 관리자

### 설정

1. 의존성 설치:
```bash
uv sync
```

2. 서버 실행:
```bash
uv run main.py
```

서버는 스트리밍 HTTP 전송을 사용하여 `http://0.0.0.0:8000`에서 시작됩니다.

## AWS 배포

이 프로젝트는 컨테이너화를 사용한 AWS 배포를 위해 설계되었습니다. 포함된 Dockerfile은 ECS, EKS, App Runner와 같은 AWS 서비스에 적합한 경량 컨테이너를 생성합니다.

### 컨테이너 빌드

```bash
docker build -t mcp-weather-server .
```

### 컨테이너 실행

```bash
docker run -p 8000:8000 mcp-weather-server
```

## 설정

MCP 서버는 다음과 같이 구성됩니다:
- **서버 이름**: MyWeatherServer
- **전송 방식**: 스트리밍 HTTP
- **포트**: 8000
- **호스트**: 0.0.0.0 (모든 인터페이스)
- **API 소스**: National Weather Service (weather.gov)

## 의존성

- `fastmcp>=2.8.1`: 최신 MCP 프레임워크
- `httpx>=0.28.1`: NWS API 호출을 위한 비동기 HTTP 클라이언트

## API 통합

서버는 National Weather Service API와 통합됩니다:
- **기본 URL**: `https://api.weather.gov`
- **형식**: GeoJSON
- **범위**: 미국만
- **인증**: 불필요
- **사용량 제한**: 적절한 User-Agent 헤더로 존중하는 사용

## 오류 처리

- 네트워크 타임아웃 보호 (30초 타임아웃)
- HTTP 상태 코드 검증
- 우아한 API 실패 처리
- 사용자 친화적인 오류 메시지
- 강력한 비동기 예외 처리

## MCP 클라이언트와의 사용

이 서버는 스트리밍 HTTP 전송을 사용하여 MCP 클라이언트(Claude Desktop 등)에 연결할 수 있습니다:

```json
{
  "mcpServers": {
    "weather": {
      "command": "http",
      "args": ["http://your-aws-endpoint:8000"]
    }
  }
}
```

## 환경 변수

기본 기능에는 환경 변수가 필요하지 않습니다. 서버는 공개 NWS API 엔드포인트를 사용합니다.

## 모니터링

서버는 프로덕션 환경에서 모니터링을 위한 내장 오류 처리 및 로깅을 포함합니다.