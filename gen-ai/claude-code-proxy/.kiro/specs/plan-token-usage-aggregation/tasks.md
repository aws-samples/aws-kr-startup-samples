# Implementation Plan: Plan Token Usage Aggregation

## Overview

이 구현 계획은 Anthropic Plan API 토큰 사용량 추적 및 집계 기능을 단계별로 구현합니다. 데이터베이스 마이그레이션부터 시작하여 핵심 로직 수정, API 확장, 테스트 순으로 진행합니다.

## Tasks

- [ ] 1. 데이터베이스 스키마 변경
  - [ ] 1.1 usage_aggregates 테이블에 provider 컬럼 추가 마이그레이션 생성
    - `alembic revision --autogenerate -m "add_provider_to_usage_aggregates"` 실행
    - provider 컬럼 추가 (String(10), nullable=False, default="bedrock")
    - 기존 인덱스 삭제 및 provider 포함 새 인덱스 생성
    - UPSERT용 유니크 제약 조건 추가 (access_key_id 사용 시 provider 포함)
    - _Requirements: 3.1, 3.3, 3.4_
  
  - [ ] 1.2 UsageAggregateModel에 provider 컬럼 추가
    - `backend/src/db/models.py` 수정
    - provider 필드 및 테이블 인덱스 정의 업데이트
    - _Requirements: 3.1_
  
  - [ ] 1.3 UsageAggregate 도메인 엔티티에 provider 필드 추가
    - `backend/src/domain/entities.py` 수정
    - _Requirements: 3.1_

- [ ] 2. Checkpoint - 마이그레이션 검증
  - 마이그레이션 적용 후 기존 데이터가 provider="bedrock"으로 설정되었는지 확인
  - 테스트 실행하여 기존 기능 정상 동작 확인

- [ ] 3. PricingConfig 프로바이더 지원 확장
  - [ ] 3.1 PricingConfig에 provider 파라미터 추가
    - `backend/src/domain/pricing.py` 수정
    - get_pricing(model, region, provider) 시그니처 변경
    - _PRICING_DATA 구조를 provider → region → model로 변경
    - Plan 기본 가격 설정 추가 (region="global", Bedrock 가격으로 폴백하지 않음)
    - _Requirements: 4.1, 4.3, 4.4_
  
  - [ ] 3.2 PricingConfig 프로바이더 조회 속성 테스트 작성
    - **Property 4: Provider-aware pricing lookup**
    - **Validates: Requirements 4.1, 4.4**
  
  - [ ] 3.3 환경 변수에서 프로바이더별 가격 로드 지원
    - PROXY_PLAN_PRICING 또는 PROXY_MODEL_PRICING JSON 형식 지원 (provider 차원 추가)
    - _load_from_json 메서드 수정
    - _Requirements: 4.2_

- [ ] 4. UsageAggregateRepository 프로바이더 지원 확장
  - [ ] 4.1 increment 메서드에 provider 파라미터 추가
    - `backend/src/repositories/usage_repository.py` 수정
    - UPSERT 쿼리에 provider 포함
    - _Requirements: 3.2_
  
  - [ ] 4.2 query 및 관련 메서드에 provider 필터 추가
    - query, query_bucket_totals, get_totals, get_monthly_usage_total, get_top_users, get_user_series 수정
    - 선택적 provider 파라미터 추가
    - _Requirements: 6.2, 6.3, 6.4_
  
  - [ ] 4.3 프로바이더 분리 집계 속성 테스트 작성
    - **Property 6: Provider-separated aggregation**
    - **Validates: Requirements 3.1, 3.2**
  
  - [ ] 4.4 _to_entity 메서드에 provider 필드 매핑 추가
    - _Requirements: 3.1_

  - [ ] 4.5 BudgetService에서 provider="bedrock" 필터 적용
    - get_monthly_usage_total 호출 시 provider="bedrock" 전달
    - _Requirements: 3.2_

- [ ] 5. TokenUsageRepository 프로바이더 명시적 저장
  - [ ] 5.1 create 메서드에서 provider 파라미터 명시적 처리
    - `backend/src/repositories/usage_repository.py` 수정
    - provider 파라미터를 명시적으로 받아 저장
    - _Requirements: 8.3_

  - [ ] 5.2 get_cost_breakdown_by_model에 provider 필터 추가
    - `backend/src/repositories/usage_repository.py` 수정
    - provider 파라미터로 TokenUsageModel.provider 필터링
    - _Requirements: 6.2, 6.3, 6.4_

- [ ] 6. Checkpoint - Repository 레이어 검증
  - 모든 테스트 통과 확인
  - 프로바이더별 집계가 분리되는지 확인

- [ ] 7. UsageRecorder Plan 사용량 기록 지원
  - [ ] 7.1 record 메서드에서 Plan 응답 기록 활성화
    - `backend/src/proxy/usage.py` 수정
    - provider=="bedrock" 조건 제거, 모든 성공 응답 기록
    - _Requirements: 1.1_
  
  - [ ] 7.2 record_streaming_usage 메서드에 provider 파라미터 추가
    - 기본값 "bedrock"으로 하위 호환성 유지
    - provider 값을 하드코딩하지 않고 전달
    - _Requirements: 2.3, 8.2, 8.4_
  
  - [ ] 7.3 _record_usage_with_cost에서 프로바이더별 가격 조회
    - provider에 따라 다른 region 사용 (plan: "global", bedrock: ctx.bedrock_region)
    - PricingConfig.get_pricing에 provider 전달
    - _Requirements: 1.3, 2.4, 5.1, 5.2, 5.3_
  
  - [ ] 7.4 _persist_usage에서 provider를 aggregate increment에 전달
    - UsageAggregateRepository.increment 호출 시 provider 포함
    - _Requirements: 3.2_
  
  - [ ] 7.5 Plan 사용량 기록 속성 테스트 작성
    - **Property 1: Plan usage recording stores correct provider and token fields**
    - **Validates: Requirements 1.1, 1.2, 2.3, 8.3**
  
  - [ ] 7.6 Plan 가격 비용 계산 속성 테스트 작성
    - **Property 2: Plan pricing used for cost calculation**
    - **Validates: Requirements 1.3, 2.4**
  
  - [ ] 7.7 하위 호환성 속성 테스트 작성
    - **Property 8: Provider parameter backward compatibility**
    - **Validates: Requirements 8.2, 8.4**

- [ ] 8. Plan 스트리밍 사용량 기록 통합
  - [ ] 8.1 _stream_plan_first에서 Plan 스트리밍 사용량 수집 및 기록
    - `backend/src/api/proxy_router.py` 수정
    - Plan 스트리밍 성공 시 StreamingUsageCollector 사용
    - 스트림 종료 시 record_streaming_usage(provider="plan") 호출
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [ ] 8.2 _build_plan_streaming_response 헬퍼 함수 생성
    - Bedrock 스트리밍과 유사한 구조로 Plan 스트리밍 응답 빌더 생성
    - 사용량 수집 및 기록 로직 포함
    - _Requirements: 2.3, 2.4_
  
  - [ ] 8.3 SSE 이벤트 파싱 속성 테스트 작성
    - **Property 3: SSE event parsing for streaming usage**
    - **Validates: Requirements 2.1, 2.2, 2.5**

- [ ] 9. Checkpoint - 핵심 기능 검증
  - Plan 정적 응답 사용량 기록 테스트
  - Plan 스트리밍 응답 사용량 기록 테스트
  - 모든 속성 테스트 통과 확인

- [ ] 10. Admin API 프로바이더 필터링 추가
  - [ ] 10.1 사용량 조회 엔드포인트에 provider 쿼리 파라미터 추가
    - `backend/src/api/admin_usage.py` 수정
    - GET /admin/usage, GET /admin/usage/top-users, GET /admin/usage/top-users/series에 provider 파라미터 추가
    - _Requirements: 6.1_
  
  - [ ] 10.2 Repository 호출 시 provider 필터 전달
    - UsageAggregateRepository와 TokenUsageRepository 호출에 provider 전달
    - _Requirements: 6.2, 6.3, 6.4_
  
  - [ ] 10.3 Admin API 프로바이더 필터링 속성 테스트 작성
    - **Property 7: Admin API provider filtering**
    - Cost breakdown에서도 provider 필터가 적용되는지 검증
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [ ] 11. CloudWatch Metrics 프로바이더 차원 추가
  - [ ] 11.1 CloudWatchMetricsEmitter에 provider 차원 추가
    - `backend/src/proxy/metrics.py` 수정
    - emit 메서드에서 Provider 차원 포함
    - _Requirements: 7.1, 7.2_

- [ ] 12. Checkpoint - 전체 기능 검증
  - 모든 테스트 통과 확인
  - 수동 테스트: Plan 요청 → 사용량 기록 → Admin API 조회

- [ ] 13. 가격 스냅샷 저장 검증
  - [ ] 13.1 가격 스냅샷 저장 속성 테스트 작성
    - **Property 5: Pricing snapshot storage for Plan usage**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [ ] 14. Final Checkpoint - 전체 테스트 및 검증
  - 모든 단위 테스트 통과 확인
  - 모든 속성 테스트 통과 확인
  - 마이그레이션 롤백 테스트
  - 문의 사항이 있으면 사용자에게 확인

## Notes

- 모든 태스크가 필수로 설정되어 포괄적인 테스트 커버리지를 확보합니다
- 각 태스크는 특정 요구사항을 참조하여 추적 가능합니다
- Checkpoint 태스크에서 점진적 검증을 수행합니다
- 속성 테스트는 설계 문서의 Correctness Properties를 검증합니다
