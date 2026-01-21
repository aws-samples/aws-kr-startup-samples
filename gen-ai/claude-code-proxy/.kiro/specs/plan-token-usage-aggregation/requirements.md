# Requirements Document

## Introduction

이 문서는 Claude Code Proxy 시스템에서 Anthropic Plan API 토큰 사용량 추적 및 집계 기능에 대한
요구사항을 정의합니다. Plan과 Bedrock 사용량을 분리해 기록/집계하고, Plan 전용 가격 설정과
가격 스냅샷을 남기며, 관리자 API와 지표에서 프로바이더별 분석이 가능해야 합니다.

## Glossary

- **Plan_API**: Anthropic에서 제공하는 Claude API 서비스 (고정 비용 구독 모델)
- **Bedrock**: AWS에서 제공하는 Claude API 서비스 (사용량 기반 과금 모델)
- **Provider**: AI 모델 제공자 (plan 또는 bedrock)
- **Usage_Recorder**: 토큰 사용량을 데이터베이스에 기록하는 컴포넌트
- **Usage_Aggregate**: 시간 버킷별로 집계된 사용량 데이터
- **Token_Usage**: 개별 요청의 토큰 사용량 레코드
- **SSE**: Server-Sent Events, 스트리밍 응답 형식
- **Streaming_Usage_Collector**: SSE 이벤트에서 사용량 메타데이터를 수집하는 컴포넌트
- **Pricing_Config**: 모델별 가격 정보를 관리하는 설정
- **Pricing_Snapshot**: token_usage에 저장되는 가격 스냅샷 정보
- **Pricing_Region**: 가격 스냅샷에서 사용하는 지역 식별자 (Plan은 "global" 또는 null)
- **Provider_Filter**: 관리자 사용량 API에서 사용하는 provider 쿼리 파라미터
- **CloudWatch_Metrics**: 프로바이더별로 분리된 운영 지표

## Requirements

### Requirement 1: Plan 정적 응답 사용량 기록

**User Story:** 관리자로서, Plan API의 비스트리밍 응답에서 토큰 사용량을 추적하고 싶습니다.
이를 통해 Plan API 사용 패턴을 분석할 수 있습니다.

#### Acceptance Criteria

1. WHEN Plan API가 성공적인 비스트리밍 응답을 반환하면, THE Usage_Recorder SHALL 응답의
   usage 필드에서 토큰 정보를 파싱하여 token_usage 테이블에 provider="plan"으로 기록해야 합니다.
2. WHEN Plan API 응답이 기록될 때, THE Usage_Recorder SHALL input_tokens, output_tokens,
   cache_read_input_tokens, cache_creation_input_tokens를 정확하게 저장해야 합니다.
3. WHEN Plan API 사용량이 기록될 때, THE Usage_Recorder SHALL 해당 요청의 비용을
   Plan 가격 설정을 사용하여 계산해야 합니다.

### Requirement 2: Plan 스트리밍 응답 사용량 기록

**User Story:** 관리자로서, Plan API의 스트리밍 응답에서도 토큰 사용량을 추적하고 싶습니다.
스트리밍은 가장 일반적인 사용 패턴이므로 정확한 추적이 필요합니다.

#### Acceptance Criteria

1. WHEN Plan API가 스트리밍 응답을 반환하면, THE Streaming_Usage_Collector SHALL
   message_start 이벤트에서 input_tokens를 수집해야 합니다.
2. WHEN Plan API 스트리밍이 완료되면, THE Streaming_Usage_Collector SHALL
   message_delta 이벤트에서 output_tokens와 캐시 토큰 정보를 수집해야 합니다.
3. WHEN Plan API 스트리밍이 종료되면, THE Usage_Recorder SHALL 수집된 사용량을
   provider="plan"으로 token_usage 테이블에 기록해야 합니다.
4. WHEN Plan API 스트리밍 사용량이 기록될 때, THE Usage_Recorder SHALL
   Plan 가격 설정을 사용하여 비용을 계산해야 합니다.
5. THE Streaming_Usage_Collector SHALL Anthropic SSE 이벤트 계약(message_start/message_delta)에
   맞는 필드 구조를 지원해야 합니다.

### Requirement 3: 프로바이더별 사용량 집계

**User Story:** 관리자로서, Plan과 Bedrock 사용량을 별도로 집계하여 각 프로바이더의 사용
패턴을 분석하고 싶습니다.

#### Acceptance Criteria

1. THE Usage_Aggregate 테이블 SHALL provider 컬럼을 포함하여 프로바이더별로 사용량을 구분해야 합니다.
2. WHEN 사용량이 집계될 때, THE Usage_Aggregate_Repository SHALL provider 값을 포함하여
   별도의 버킷에 저장해야 합니다.
3. WHEN 기존 usage_aggregates 데이터가 마이그레이션될 때, THE System SHALL
   기존 레코드에 provider="bedrock"을 설정해야 합니다.
4. THE Usage_Aggregate 테이블 SHALL (bucket_type, bucket_start, user_id, provider) 조합에 대한
   유니크 키를 가져야 하며, access_key_id 기반 집계를 유지한다면 해당 키에도 provider를 포함해야 합니다.

### Requirement 4: Plan 가격 설정

**User Story:** 관리자로서, Plan API에 대한 별도의 가격 설정을 구성하고 싶습니다. Plan과
Bedrock은 다른 가격 체계를 가지고 있기 때문입니다.

#### Acceptance Criteria

1. THE Pricing_Config SHALL provider 파라미터를 받아 Plan 또는 Bedrock 가격을 반환해야 합니다.
2. THE Pricing_Config SHALL Plan 가격을 PROXY_PLAN_PRICING 환경 변수 또는
   PROXY_MODEL_PRICING의 provider 확장 형식에서 로드할 수 있어야 합니다.
3. WHEN Plan 가격이 설정되지 않은 경우, THE Pricing_Config SHALL 기본 Plan 가격을 사용해야 합니다.
4. THE Pricing_Config SHALL Plan 가격의 region 값을 "global" 또는 null로 다룰 수 있어야 합니다.

### Requirement 5: 가격 스냅샷 저장

**User Story:** 관리자로서, 비용 분석과 감사 추적을 위해 요청 시점의 가격 스냅샷을 확인하고 싶습니다.

#### Acceptance Criteria

1. WHEN token_usage 레코드가 생성될 때, THE System SHALL Pricing_Snapshot 정보를 저장해야 합니다
   (pricing_region, pricing_model_id, pricing_effective_date, pricing_*_price_per_million).
2. WHEN Plan 사용량이 기록될 때, THE System SHALL pricing_region을 "global" 또는 null로 저장해야 합니다.
3. WHEN Plan 사용량이 기록될 때, THE System SHALL pricing_model_id를 Plan 가격 키로 저장해야 합니다.

### Requirement 6: 관리자 API 프로바이더 필터링

**User Story:** 관리자로서, 사용량 조회 API에서 프로바이더별로 필터링하고 싶습니다. 이를 통해
Plan과 Bedrock 사용량을 개별적으로 분석할 수 있습니다.

#### Acceptance Criteria

1. WHEN 관리자가 사용량 API를 호출할 때, THE API SHALL 선택적 provider 파라미터를 지원해야 합니다.
2. WHEN provider 파라미터가 "plan"으로 설정되면, THE API SHALL Plan 사용량만 반환해야 합니다.
3. WHEN provider 파라미터가 "bedrock"으로 설정되면, THE API SHALL Bedrock 사용량만 반환해야 합니다.
4. WHEN provider 파라미터가 제공되지 않으면, THE API SHALL 모든 프로바이더의 사용량을 합산하여 반환해야 합니다.

### Requirement 7: CloudWatch 지표 프로바이더 분리

**User Story:** 운영자로서, Plan과 Bedrock 지표를 분리하여 모니터링하고 싶습니다.

#### Acceptance Criteria

1. THE CloudWatch_Metrics SHALL provider를 차원(dimension)으로 포함하거나
   provider별 네임스페이스로 분리해야 합니다.
2. THE System SHALL Plan과 Bedrock 지표를 동일한 시계열로 혼합하지 않아야 합니다.

### Requirement 8: 데이터 무결성 및 하위 호환성

**User Story:** 시스템 관리자로서, 새로운 기능이 기존 Bedrock 사용량 추적에 영향을 주지 않고
안전하게 배포되기를 원합니다.

#### Acceptance Criteria

1. WHEN 새로운 마이그레이션이 적용될 때, THE System SHALL 기존 usage_aggregates 데이터를 보존해야 합니다.
2. THE Usage_Recorder SHALL provider 파라미터의 기본값을 "bedrock"으로 설정하여 하위 호환성을 유지해야 합니다.
3. WHEN token_usage 레코드가 생성될 때, THE System SHALL provider 값을 명시적으로 저장해야 합니다.
4. THE Usage_Recorder SHALL 스트리밍 사용량 기록 시 provider 값을 하드코딩하지 않아야 합니다.
5. IF 마이그레이션 중 오류가 발생하면, THEN THE System SHALL 롤백을 지원하고 데이터 손실을 방지해야 합니다.
