# AWS Bedrock Pricing Audit

## Problem Statement
현재 `backend/src/domain/pricing.py`에 하드코딩된 기본 가격이 실제 AWS Bedrock 가격과 일치하는지 확인이 필요합니다.

## User Stories

### US-1: 가격 정확성 검증
**As a** 시스템 관리자
**I want** 현재 설정된 가격이 AWS 공식 가격과 일치하는지 확인하고 싶습니다
**So that** 사용자에게 정확한 비용을 청구할 수 있습니다

**Acceptance Criteria:**
- AC1: Claude Sonnet 4 모델의 input/output 가격이 AWS 공식 가격과 일치
- AC2: Claude Haiku 모델의 input/output 가격이 AWS 공식 가격과 일치
- AC3: Claude Opus 모델의 input/output 가격이 AWS 공식 가격과 일치
- AC4: Cache read/write 가격이 AWS 공식 가격과 일치

### US-2: 가격 업데이트 용이성
**As a** 개발자
**I want** 가격 변경 시 쉽게 업데이트할 수 있는 구조를 원합니다
**So that** AWS 가격 변경에 빠르게 대응할 수 있습니다

**Acceptance Criteria:**
- AC1: 환경변수로 가격 오버라이드 가능
- AC2: 런타임 가격 리로드 API 존재

## Functional Requirements

### FR-1: 가격 데이터 검증
- 현재 하드코딩된 가격과 AWS 공식 가격 비교
- 불일치 항목 식별 및 수정

### FR-2: 가격 구조 검토
- 지원 모델 목록 확인 (Opus, Sonnet, Haiku)
- 지원 리전 확인 (ap-northeast-2 등)
- 토큰 타입별 가격 구조 확인 (input, output, cache_read, cache_write)

## Non-Functional Requirements

### NFR-1: 정확성
- 가격은 소수점 6자리까지 정확해야 함
- USD 기준 per 1M tokens

## Out of Scope
- 새로운 모델 추가
- 새로운 리전 추가
- 가격 자동 동기화 기능
