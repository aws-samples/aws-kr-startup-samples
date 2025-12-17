---
name: "fetch-openapi"
displayName: "Fetch OpenAPI Specs"
description: "OpenAPI(JSON) 스펙을 fetch로 불러와 엔드포인트/스키마를 근거로 API 호출 코드를 정확히 작성하도록 돕습니다."
keywords: ["openapi", "swagger", "api spec", "openapi.json", "rest api", "endpoint", "internal api"]
mcpServers: ["fetch"]
---

# Onboarding
## Step 1: fetch MCP 서버 준비 확인
- 이 Power는 `fetch` MCP 서버를 사용한다.
- (중요) 사내 네트워크/내부 URL에 접근 가능한 환경에서만 사용하고, 허용된 도메인만 fetch한다(보안).
- OpenAPI 위치는 다음과 같다.
    <!-- - 사용자 관리: http://orderhost:8100/openapi.json -->
    <!-- - 상품 관리: http://producthost:8200/openapi.json -->

## Step 2: 사용 방법(필수 워크플로)
사용자가 OpenAPI 위치 이름을 주면 그에 대한 경로에 접속한 후 fetch해서, 아래 순서로 행동한다.

1) `@fetch` 도구로 `openapi.json`을 가져온다.
   - 스펙이 길면(또는 응답이 잘리면) `start_index`를 증가시키며 여러 번 읽어 전체를 확보한다.
2) 가져온 JSON에서 다음을 추출해 "근거 기반"으로 정리한다.
   - base URL / servers(있다면), paths, method, operationId, requestBody schema, responses
3) 코드 작성 시 반드시 아래 규칙을 따른다.
   - 요청한 세부 항목에 대해서만 코드를 작성
   - 요청 바디는 schema에 맞춰 타입/필드를 정확히 사용
   - 필요한 query/path 파라미터를 누락하지 않음
   - 응답/에러(예: 4xx/5xx, 422 validation)를 처리
4) 사용자가 여러 내부 API 스펙 URL을 제공하면,
   - 각 스펙을 "서비스명/URL" 기준으로 구분해 요약하고,
   - 어떤 호출이 어느 서비스의 어느 operationId인지 명확히 표시한다.

# Best Practices
## OpenAPI 기반 코드 생성 체크리스트
- (필수) endpoint + method를 스펙의 paths에서 정확히 매칭
- (필수) requestBody content-type 확인(application/json 등)
- (필수) operationId를 함수명/메서드명에 반영(가능하면)
- (권장) 공통 HTTP 클라이언트(axios/fetch/httpx 등) 래핑 + 타임아웃 + 재시도 정책
- (권장) 인증 헤더/토큰 처리 방식은 스펙/사내 규칙에 맞춤(불명확하면 질문)
