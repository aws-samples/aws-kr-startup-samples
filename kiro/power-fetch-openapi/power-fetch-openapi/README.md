# fetch-openapi Power

Kiro Custom Power로 OpenAPI(JSON) 스펙을 fetch로 불러와 엔드포인트/스키마를 근거로 API 호출 코드를 정확히 작성하도록 돕습니다.

## 개요

이 Power는 내부 API의 OpenAPI 스펙을 가져와서 정확한 API 호출 코드를 생성할 수 있도록 지원합니다. 스펙 기반으로 엔드포인트, 요청/응답 스키마, 파라미터 등을 자동으로 파악하여 코드 작성 시 실수를 줄입니다.

## 주요 기능

- OpenAPI JSON 스펙 자동 fetch
- 엔드포인트 및 스키마 기반 코드 생성
- 요청 바디, 쿼리 파라미터, 경로 파라미터 정확한 매칭
- 응답 및 에러 처리 코드 포함
- 여러 내부 API 스펙 동시 관리

## 설치 방법

1. 이 Power를 Kiro의 Powers로 등록합니다. 설치합니다
2. `fetch` MCP 서버가 자동으로 구성됩니다 (uvx 필요)
3. 사내 네트워크/내부 URL에 접근 가능한 환경에서 사용하세요

## 사용 방법

### 1. API 코드 생성

아래와 같이 요청을 하세요:
```
사용자 조회 API 호출 코드를 TypeScript로 작성해줘
```
* '사용자 조회'에 대해서는 POWER.md 에 미리 URL을 정의해서 로딩하거나, Kiro 또는 Chat 창에 URL을 알려줘야 합니다. 

```
http://orderhost:8100/openapi.json API를 사용해서 주문 생성 코드를 작성해줘
```

```
상품 목록 조회 API를 Python으로 작성하고 에러 처리도 포함해줘
```

### 2. 여러 API 스펙 사용

여러 내부 서비스의 스펙을 동시에 활용할 수 있습니다:

```
사용자 관리와 
http://producthost:8200/openapi.json 스펙을 가져와서
사용자 생성 후 상품을 등록하는 플로우 코드를 작성해줘
```

이 Power의 Workflow와 Best Practices 는 아래와 같이 정의되어 있습니다.

## 워크플로

1. **스펙 가져오기**: `@fetch` 도구로 OpenAPI JSON을 fetch
2. **스펙 분석**: paths, methods, schemas, parameters 추출
3. **코드 생성**: 스펙 기반으로 정확한 API 호출 코드 작성
4. **검증**: 요청/응답 타입, 에러 처리 포함 확인

## Best Practices

- ✅ endpoint + method를 스펙의 paths에서 정확히 매칭
- ✅ requestBody content-type 확인 (application/json 등)
- ✅ operationId를 함수명/메서드명에 반영
- ✅ 공통 HTTP 클라이언트 래핑 + 타임아웃 + 재시도 정책
- ✅ 인증 헤더/토큰 처리 방식은 스펙/사내 규칙에 맞춤

## 보안 주의사항

- 사내 네트워크/내부 URL에 접근 가능한 환경에서만 사용
- 허용된 도메인만 fetch (보안 정책 준수)
- 민감한 API 키나 토큰은 환경 변수로 관리

## 키워드

`openapi`, `api spec`, `openapi.json`, `rest api`, `endpoint`, `internal api`

