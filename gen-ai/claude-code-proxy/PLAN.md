# 메트릭 수집 개선 계획

## 개요

CloudWatch와 OTEL(OTLP) 두 경로로 메트릭을 내보내며, **가장 중요한 목표는 사용자별 토큰 사용량 가시화**입니다. 이를 위해 **저카디널리티(운영 지표)**와 **고카디널리티(사용자 지표)**를 분리 설계합니다.

- **CloudWatch**: 운영/알림용 저카디널리티 메트릭 중심
- **OTEL**: 저카디널리티 + 사용자별 고카디널리티 메트릭

---

## 작업 진행 현황 (다음 세션용)

| Phase | 내용 | 상태 |
|-------|------|------|
| **Phase 1** | Core Metrics 개선 (CloudWatch) | ✅ **완료** |
| **Phase 2** | OTEL 메트릭 추가 | ⏳ **다음** |
| **Phase 3** | 인프라 (ADOT sidecar, AMP 등) | ⏸ 선택 |

### Phase 1 완료 사항
- `CloudWatchMetricsEmitter`: `proxy.requests`, `proxy.latency`, `proxy.ttft`, `proxy.tokens`, `proxy.cost`, `proxy.errors`, `proxy.fallbacks` 7종 메트릭
- `emit(response, latency_ms, model, cost, stream, ttft_ms, fallback_reason)` 시그니처 확장
- Plan/Bedrock 토큰·cache_read/cache_write·비용 수집, 스트리밍 TTFT 측정, fallback_reason 전달
- `PROXY_CLOUDWATCH_METRICS_ENABLED`, `PROXY_CLOUDWATCH_NAMESPACE` 환경변수 on/off

### 다음 세션에서 이어갈 작업 (Phase 2)
1. **config**: `PROXY_OTEL_*` 설정 추가 (endpoint, protocol, service_name, export_interval 등)
2. **OTELMetricsEmitter** 구현: CloudWatch와 동일한 `emit()` 인터페이스, Tier 1 Core 메트릭 전송
3. **CompositeMetricsEmitter**: CloudWatch + OTEL 둘 다 호출, `PROXY_OTEL_METRICS_ENABLED`로 OTEL on/off
4. **PROXY_OTEL_USER_METRICS_ENABLED**: `proxy.user.requests`, `proxy.user.tokens`, `proxy.user.cost` (Tier 2, OTEL 전용)
5. **pyproject.toml**: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc` 등 의존성 추가
6. **UsageRecorder / proxy_router**: `CompositeMetricsEmitter` 주입, 기존 `CloudWatchMetricsEmitter` 단일 사용에서 전환

> Phase 2부터는 `backend/src/proxy/metrics.py`에 OTEL 관련 클래스 추가 및 `config.py`에 OTEL env 확장이 필요합니다. `emit()` 시그니처는 Phase 1에서 이미 확장되어 있으므로 그대로 사용 가능합니다.

---

## 설계 원칙

1) **Two-tier 메트릭**
- Tier 1 (Core): 운영 지표. CloudWatch + OTEL 모두 전송
- Tier 2 (User): 사용자별 지표. OTEL 전용 (CloudWatch는 기본 비활성)

2) **카디널리티 제어**
- CloudWatch Dimension에 **user_id/access_key_id** 금지
- OTEL에서는 사용자 라벨 허용하되 **필요 시 해시/마스킹**

3) **표준화된 축**
- provider: `plan | bedrock`
- status: `success | error`
- token_type: `input | output | cache_read | cache_write`
- model: **pricing_model_id로 정규화** (Bedrock region별 alias 포함)

4) **스트리밍 메트릭 분리**
- streaming 여부를 `stream` dimension/label로 구분
- TTFT(Time To First Token) 별도 히스토그램

5) **CloudWatch 태그 오해 방지**
- 커스텀 메트릭 자체에 태그를 부착할 수 없음
- 태그처럼 쓰고 싶다면 결국 **Dimension** 사용 → 고카디널리티 주의

---

## CloudWatch 메트릭 개념 (간단 요약)

| 개념 | 역할 | 비유 |
|------|------|------|
| **Namespace** | 메트릭 그룹 격리 | 엑셀 워크북 |
| **Metric** | 측정 대상 | 엑셀 시트 |
| **Dimension** | 필터/그룹핑 | 엑셀 필터 컬럼 |
| **Unit** | 값 단위 | 셀 서식 |

### ⚠️ Dimension 주의사항
- Dimension 조합마다 **별도 시계열** 생성됨
- CloudWatch에서는 **고카디널리티 필드 금지**
  - ❌ user_id, request_id, access_key_id
  - ✅ provider, model, status, error_type, stream

---

## 현재 상태 (AS-IS)

### CloudWatch 메트릭 (`CloudWatchMetricsEmitter`)

| 메트릭 | Dimensions | 조건 | 문제점 |
|--------|------------|------|--------|
| `RequestCount` | Provider | 항상 | - |
| `RequestLatency` | Provider | 항상 | model 정보 없음 |
| `ErrorCount` | ErrorType, Provider | 에러 시 | - |
| `FallbackCount` | Provider | fallback 시 | - |
| `BedrockTokensUsed` | TokenType, Provider | Bedrock만 | ❌ Plan API 토큰 누락 |

**Namespace**: `ClaudeCodeProxy`

### 제한사항
- Plan API 토큰 사용량 미수집
- 비용(cost) 메트릭 없음
- cache_read/cache_write 토큰 구분 없음
- model별 분석 불가
- 사용자별 가시화 경로 없음

---

## 목표 상태 (TO-BE)

### Tier 1: Core Metrics (저카디널리티, CloudWatch + OTEL)

| 메트릭 | 타입 | 단위 | Dimensions/Labels |
|--------|------|------|-------------------|
| `proxy.requests` | Counter | count | provider, model, status, stream |
| `proxy.latency` | Histogram | ms | provider, model, status, stream |
| `proxy.ttft` | Histogram | ms | provider, model (streaming only) |
| `proxy.tokens` | Counter | token | provider, model, token_type |
| `proxy.cost` | Counter | USD | provider, model |
| `proxy.errors` | Counter | count | provider, error_type |
| `proxy.fallbacks` | Counter | count | from_provider, to_provider, reason |

### Tier 2: User Metrics (고카디널리티, OTEL only)

| 메트릭 | 타입 | 단위 | Labels |
|--------|------|------|--------|
| `proxy.user.requests` | Counter | count | user_id, provider, model, status |
| `proxy.user.tokens` | Counter | token | user_id, provider, model, token_type |
| `proxy.user.cost` | Counter | USD | user_id, provider, model |

> user_id는 OTEL에서만 사용하며, 필요 시 해시/마스킹 옵션 제공.

---

## CloudWatch 메트릭 변경

### 변경 전

```python
metrics = [
    {"MetricName": "RequestCount", "Dimensions": [{"Name": "Provider", "Value": provider}]},
    {"MetricName": "BedrockTokensUsed", "Dimensions": [{"Name": "TokenType", "Value": "input"}]},
]
```

### 변경 후 (Core Metrics)

```python
metrics = [
    {"MetricName": "proxy.requests", "Dimensions": [
        {"Name": "Provider", "Value": provider},
        {"Name": "Model", "Value": model},
        {"Name": "Status", "Value": status},
        {"Name": "Stream", "Value": stream},
    ]},
    {"MetricName": "proxy.tokens", "Dimensions": [
        {"Name": "Provider", "Value": provider},
        {"Name": "Model", "Value": model},
        {"Name": "TokenType", "Value": "input"},
    ]},
    {"MetricName": "proxy.cost", "Dimensions": [
        {"Name": "Provider", "Value": provider},
        {"Name": "Model", "Value": model},
    ]},
]
```

### 주요 변경점

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 메트릭 이름 | `RequestCount` | `proxy.requests` |
| Plan API 토큰 | ❌ 미수집 | ✅ 수집 |
| Model dimension | ❌ 없음 | ✅ 추가 |
| Cost 메트릭 | ❌ 없음 | ✅ 추가 |
| Cache 토큰 구분 | ❌ 없음 | ✅ cache_read, cache_write |
| Streaming 구분 | ❌ 없음 | ✅ stream |
| TTFT | ❌ 없음 | ✅ proxy.ttft |
| 사용자별 지표 | ❌ 없음 | ✅ OTEL 전용 |

---

## OTEL 메트릭 추가

### 아키텍처 (Push)

```
┌─────────────────────────────────────────────────────────────┐
│                     ECS Task                                │
│  ┌─────────────────┐      ┌─────────────────────────────┐   │
│  │  Backend        │      │  ADOT Collector (Sidecar)   │   │
│  │                 │ OTLP │                             │   │
│  │  OTELEmitter ───┼──────▶  receivers:                │   │
│  │                 │ :4317│    otlp: grpc              │   │
│  │                 │      │  exporters:                 │   │
│  └─────────────────┘      │    - prometheusremotewrite │   │
│                           │    - awsemf (optional)      │   │
│                           └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              ┌──────────┐     ┌──────────┐     ┌──────────┐
              │   AMP    │     │ Grafana  │     │Prometheus│
              │          │     │  Cloud   │     │ (self)   │
              └──────────┘     └──────────┘     └──────────┘
```

- 기본은 **Push(OTLP)** 방식
- Pull(scrape) 방식은 별도 `/metrics` 엔드포인트를 열어야 함

### Collector가 여러 개인 경우
- **권장**: 인스턴스마다 Sidecar 1개 → 앱은 `localhost:4317`로만 전송
- **Gateway + LB**: 중앙 Collector 여러 대 + LB, 앱은 LB 주소 하나만 사용
- **주의**: 앱이 여러 Collector로 동시에 push하면 **중복 집계** 위험

---

## 환경변수

```bash
# CloudWatch (기본 활성화)
PROXY_CLOUDWATCH_METRICS_ENABLED=true
PROXY_CLOUDWATCH_NAMESPACE=ClaudeCodeProxy

# OTEL (기본 비활성)
PROXY_OTEL_METRICS_ENABLED=false
PROXY_OTEL_ENDPOINT=http://localhost:4317
PROXY_OTEL_PROTOCOL=grpc
PROXY_OTEL_SERVICE_NAME=claude-code-proxy
PROXY_OTEL_HEADERS=
PROXY_OTEL_INSECURE=true
PROXY_OTEL_EXPORT_INTERVAL_MS=10000
PROXY_OTEL_EXPORT_TIMEOUT_MS=3000

# OTEL 고카디널리티 사용자 지표
PROXY_OTEL_USER_METRICS_ENABLED=false
```

---

## 구현 계획

### Phase 1: Core Metrics 개선 (CloudWatch + OTEL 공통 스키마) — ✅ 완료

1. `CloudWatchMetricsEmitter` 개선
   - `proxy.*` 이름으로 변경
   - model, status, stream dimension 추가
   - Plan API 토큰 수집 추가
   - Cost/Cache 토큰 추가
   - TTFT/Latency 분리

2. `emit()` 시그니처 확장
   ```python
   # 변경 전
   async def emit(self, response: ProxyResponseProtocol, latency_ms: int)

   # 변경 후 (예시)
   async def emit(
       self,
       ctx: RequestContext,
       response: ProxyResponseProtocol,
       latency_ms: int,
       model: str,
       cost: Decimal,
       stream: bool,
       ttft_ms: int | None,
       fallback_reason: str | None,
   )
   ```

### Phase 2: OTEL 메트릭 추가 — ⏳ 다음

1. `OTELMetricsEmitter` 구현 (동일 인터페이스)
2. `CompositeMetricsEmitter` 구현 (CloudWatch + OTEL 호출)
3. `PROXY_OTEL_METRICS_ENABLED`로 on/off 제어
4. `PROXY_OTEL_USER_METRICS_ENABLED`로 사용자 지표 on/off

### Phase 3: 인프라 (선택)

1. CDK에 ADOT Collector sidecar 추가
2. AMP workspace 생성 (선택)

---

## 파일 변경 목록

| 파일 | 변경 내용 | Phase |
|------|----------|-------|
| `backend/src/config.py` | CloudWatch: `PROXY_CLOUDWATCH_*` 추가. OTEL: `PROXY_OTEL_*` 추가 | 1 ✅ / 2 ⏳ |
| `backend/src/proxy/metrics.py` | CloudWatch 개선 (proxy.* 7종). OTEL: `OTELMetricsEmitter`, `CompositeMetricsEmitter` | 1 ✅ / 2 ⏳ |
| `backend/src/proxy/usage.py` | emit() 호출 시 model/cost/stream/ttft/fallback_reason 전달 | 1 ✅ |
| `backend/src/api/proxy_router.py` | streaming emit 시 TTFT 측정 & fallback_reason 전달 | 1 ✅ |
| `backend/pyproject.toml` | OTEL 의존성 추가 | 2 ⏳ |
| `infra/stacks/compute_stack.py` | ADOT sidecar (선택) | 3 ⏸ |

---

## 마이그레이션 고려사항

### CloudWatch 메트릭 이름 변경

기존 대시보드/알람이 있다면 영향받음:
- `RequestCount` → `proxy.requests`
- `BedrockTokensUsed` → `proxy.tokens`

**옵션 A**: 기존 메트릭 유지 + 새 메트릭 추가 (중복)
**옵션 B**: 새 메트릭으로 완전 교체 (권장)

### 사용자별 지표

- CloudWatch는 고카디널리티 때문에 **기본 비활성**
- OTEL의 `proxy.user.*`로 가시화
