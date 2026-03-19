# AWS Bedrock Pricing Audit - Design

## Overview
현재 시스템의 가격 설정을 AWS 공식 가격과 비교하여 정확성을 검증합니다.

## Current Implementation Analysis

### 가격 설정 위치
- **파일**: `backend/src/domain/pricing.py`
- **클래스**: `PricingConfig._load_defaults()`
- **환경변수 오버라이드**: `PROXY_MODEL_PRICING` (JSON)

### 현재 하드코딩된 가격 (per 1M tokens, USD)

| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| claude-opus-4-5 | $5.00 | $25.00 | $6.25 | $0.50 |
| claude-opus-4-6 | $5.00 | $25.00 | $6.25 | $0.50 |
| claude-sonnet-4-5 | $3.00 | $15.00 | $3.75 | $0.30 |
| claude-sonnet-4-6 | $3.00 | $15.00 | $3.75 | $0.30 |
| claude-haiku-4-5 | $1.00 | $5.00 | $1.25 | $0.10 |

### 지원 리전
- Bedrock: `ap-northeast-2` (기본)
- Plan API: `global`

## AWS Official Pricing Reference

### AWS Bedrock Claude Pricing (2025년 기준)
참조: https://aws.amazon.com/bedrock/pricing/

**Claude 4 Sonnet (claude-sonnet-4-20250514)**
- Input: $3.00 / 1M tokens
- Output: $15.00 / 1M tokens

**Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)**
- Input: $3.00 / 1M tokens
- Output: $15.00 / 1M tokens

**Claude 3.5 Haiku (claude-3-5-haiku-20241022)**
- Input: $0.80 / 1M tokens
- Output: $4.00 / 1M tokens

**Prompt Caching (Bedrock)**
- Cache write: 1.25x input price
- Cache read: 0.10x input price

## Verification Checklist

### 1. Sonnet 가격 검증
- [ ] Input price: $3.00 ✓
- [ ] Output price: $15.00 ✓
- [ ] Cache write: $3.75 (3.00 × 1.25) ✓
- [ ] Cache read: $0.30 (3.00 × 0.10) ✓

### 2. Haiku 가격 검증
- [ ] Input price: 현재 $1.00 → AWS 공식 $0.80 ⚠️
- [ ] Output price: 현재 $5.00 → AWS 공식 $4.00 ⚠️
- [ ] Cache write: 현재 $1.25 → 수정 필요 $1.00 (0.80 × 1.25)
- [ ] Cache read: 현재 $0.10 → 수정 필요 $0.08 (0.80 × 0.10)

### 3. Opus 가격 검증
- [ ] Input price: $5.00 (확인 필요)
- [ ] Output price: $25.00 (확인 필요)
- [ ] Cache write: $6.25 (5.00 × 1.25)
- [ ] Cache read: $0.50 (5.00 × 0.10)

## Proposed Changes

### pricing.py 수정 사항

```python
# Haiku 가격 수정
"claude-haiku-4-5": ModelPricing(
    model_id="claude-haiku-4-5",
    region=default_region,
    input_price_per_million=Decimal("0.80"),   # 변경: 1.00 → 0.80
    output_price_per_million=Decimal("4.00"),  # 변경: 5.00 → 4.00
    cache_write_price_per_million=Decimal("1.00"),  # 변경: 1.25 → 1.00
    cache_read_price_per_million=Decimal("0.08"),   # 변경: 0.10 → 0.08
    effective_date=effective_date,
),
```

## Data Flow

```
환경변수 PROXY_MODEL_PRICING (JSON)
    ↓
PricingConfig._load_from_json()
    ↓ (merge=True)
PricingConfig._PRICING_DATA
    ↓
CostCalculator.calculate_cost()
    ↓
UsageRecorder → token_usage 테이블
```

## Testing Strategy

1. **단위 테스트**: 가격 계산 정확성 검증
2. **통합 테스트**: 환경변수 오버라이드 동작 확인
3. **수동 검증**: AWS 콘솔에서 실제 가격 확인

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| AWS 가격 변경 | 환경변수로 오버라이드 가능 |
| 리전별 가격 차이 | 리전별 가격 설정 지원 |
| 새 모델 출시 | `PROXY_MODEL_PRICING`으로 추가 가능 |
