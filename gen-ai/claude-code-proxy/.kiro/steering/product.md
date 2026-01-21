---
inclusion: always
---

# Product Overview

Claude Code Proxy is an enterprise LLM gateway service that routes requests from Claude Code clients to AI providers (Anthropic Plan API and Amazon Bedrock) with automatic failover, usage tracking, budget enforcement, and multi-tenant access management.

**Key Value Proposition**: Organizations can optimize costs by combining fixed-cost Anthropic Plan API with pay-per-use Bedrock, while maintaining centralized control over access, budgets, and usage visibility.

## Core Capabilities

| Feature | Description |
|---------|-------------|
| Automatic Failover | Primary: Anthropic Plan API → Fallback: Amazon Bedrock on rate limits/failures |
| Usage Tracking | Per-user/key token metrics with hourly/daily aggregation |
| Admin Dashboard | Web UI for user/key management, Bedrock credentials, usage analytics |
| Multi-tenant Access | Unique access keys per user with optional per-key Bedrock credentials |

## User Personas

| Persona | Interaction | Key Actions |
|---------|-------------|-------------|
| End User | Claude Code client | Set `ANTHROPIC_BASE_URL` to proxy endpoint with access key |
| Admin | Web dashboard | Manage users/keys, register Bedrock credentials, view usage |

## API Contract

### Primary Endpoint

```
POST /ak/{access_key}/v1/messages
```

### Implementation Rules

| Rule | Requirement |
|------|-------------|
| Access Key Location | MUST be embedded in URL path (`/ak/{access_key}/...`) |
| API Compatibility | Request/response MUST match Anthropic Messages API schema exactly |
| Streaming | MUST support both streaming (`stream: true`) and non-streaming responses |
| Headers | Passthrough: `x-api-key`, `authorization`, `anthropic-version`, `anthropic-beta`, `content-type` |

### Routing Strategies

| Strategy | Behavior |
|----------|----------|
| `plan_first` (default) | Try Anthropic Plan API first, fallback to Bedrock on rate limit/failure |
| `bedrock_only` | Skip Plan API entirely, use only Bedrock |

### Circuit Breaker Behavior

| Aspect | Specification |
|--------|---------------|
| Scope | Per-access-key (independent state per key) |
| Triggers | 429, 500-504, connection failures |
| Threshold | 3 failures within 60s (`PROXY_CIRCUIT_FAILURE_THRESHOLD`) |
| Recovery | Auto-closes after 30 min (`PROXY_CIRCUIT_RESET_TIMEOUT`) |
| State | In-memory only; resets on backend restart |

### Fallback Decision Matrix

| HTTP Status | Trigger Fallback? | Reason |
|-------------|-------------------|--------|
| 429 | YES | Rate limit exceeded |
| 500-504 | YES | Server errors |
| Connection timeout | YES | Network failure |
| 400, 401, 403, other 4xx | NO | Client/auth errors (do not retry) |

## Data Model

### Entity Hierarchy

```
User (admin accounts)
  └─ AccessKey[] (API keys, soft-deletable)
       ├─ BedrockKey (optional 1:1, KMS-encrypted)
       └─ TokenUsage[] (per-request events)
            └─ UsageAggregate[] (hourly/daily rollups)
```

### Data Handling Patterns

| Data Type | Pattern | Implementation |
|-----------|---------|----------------|
| Access Keys | Hashed storage | HMAC-SHA256 with `PROXY_KEY_HASHER_SECRET` |
| Bedrock Credentials | Encrypted storage | KMS envelope encryption |
| Deleted Records | Soft delete | Set `deleted_at` timestamp |
| Admin Passwords | Hashed storage | SHA256 |

### Soft Delete Convention (CRITICAL)

All queries on soft-deletable entities MUST include:
```python
.where(Model.deleted_at.is_(None))
```

Affected tables: `access_keys`, `users`

## Usage Tracking

### Per-Request Fields

| Field | Type | Description |
|-------|------|-------------|
| `input_tokens` | int | Tokens in request |
| `output_tokens` | int | Tokens in response |
| `cache_read_input_tokens` | int | Cache read tokens |
| `cache_creation_input_tokens` | int | Cache write tokens |
| `provider` | enum | `plan` or `bedrock` |
| `is_fallback` | bool | True if served by fallback provider |
| `access_key_id` | FK | Associated access key (SET NULL on key deletion) |
| `estimated_cost_usd` | Decimal(12,6) | Total estimated cost |
| `pricing_*` | various | Pricing snapshot at request time |

### Aggregation

- Bucket types: `minute`, `hour`, `day`, `week`, `month`
- Includes cache token tracking and cost breakdown by token type

## Budget Management

### Monthly Budget Enforcement

| Aspect | Specification |
|--------|---------------|
| Scope | Per-user monthly limit in USD |
| Timezone | KST (UTC+9) - resets on 1st of each month |
| Enforcement | Bedrock requests blocked when exceeded |
| Fail-open | Budget check failures allow requests by default |
| Cache TTL | 60 seconds (`PROXY_BUDGET_CACHE_TTL`) |

### Budget Exceeded Response (HTTP 429)

```json
{
  "type": "error",
  "error": {
    "type": "rate_limit_error",
    "message": "Monthly budget exceeded. Current usage: $50.00, Budget limit: $50.00. Budget resets on 2025-02-01 00:00:00 KST."
  }
}
```

## Cost Visibility

### Pricing Configuration

- Source: `PROXY_MODEL_PRICING` environment variable (JSON)
- Supports per-region, per-model pricing
- Runtime reload: `POST /api/pricing/reload`
- Precision: 6 decimal places

### Cost Calculation

```
cost = (tokens / 1,000,000) * price_per_million
```

Token types: `input`, `output`, `cache_write`, `cache_read`

## Implementation Guidelines

### When Adding New Features

1. Proxy behavior changes → Update `backend/src/proxy/router.py`
2. New usage fields → Add migration, update `TokenUsage` model, update repositories
3. Budget logic changes → Modify `backend/src/proxy/budget.py`
4. Cost calculation changes → Update `backend/src/domain/cost_calculator.py`

### Error Response Format

All error responses MUST follow Anthropic's error schema:
```json
{
  "type": "error",
  "error": {
    "type": "<error_type>",
    "message": "<human_readable_message>"
  }
}
```

### Testing Requirements

- Circuit breaker: Test state transitions (closed → open → half-open → closed)
- Budget: Test enforcement, cache invalidation, timezone handling
- Fallback: Test all trigger conditions in decision matrix
- Streaming: Test both SSE streaming and non-streaming responses
