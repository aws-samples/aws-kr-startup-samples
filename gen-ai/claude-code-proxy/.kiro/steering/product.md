---
inclusion: always
---

# Product Overview

Claude Code Proxy routes requests from Claude Code to AI providers with automatic failover, usage tracking, and multi-tenant access management.

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

When implementing or modifying proxy behavior, follow these constraints:

| Rule | Requirement |
|------|-------------|
| Access Key Location | MUST be embedded in URL path (`/ak/{access_key}/...`) |
| API Compatibility | Request/response MUST match Anthropic Messages API schema exactly |
| Streaming | MUST support both streaming (`stream: true`) and non-streaming responses |
| Headers | Passthrough: `x-api-key`, `authorization`, `anthropic-version`, `anthropic-beta`, `content-type` |

### Circuit Breaker Behavior

| Aspect | Specification |
|--------|---------------|
| Scope | Per-access-key (independent state per key) |
| Triggers | 429, 500-504, connection failures |
| Threshold | 3 failures within 60s (configurable via `PROXY_CIRCUIT_FAILURE_THRESHOLD`) |
| Recovery | Auto-closes after 30 min (configurable via `PROXY_CIRCUIT_RESET_TIMEOUT`) |
| State | In-memory only; resets on backend restart |

### Fallback Decision Matrix

| HTTP Status | Trigger Fallback? | Reason |
|-------------|-------------------|--------|
| 429 | YES | Rate limit exceeded |
| 500-504 | YES | Server errors |
| Connection timeout | YES | Network failure |
| 400 | NO | Invalid request (user error) |
| 401/403 | NO | Auth failure (user error) |
| Other 4xx | NO | Client errors |

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
| Deleted Records | Soft delete | Set `deleted_at` timestamp; always filter with `deleted_at IS NULL` |
| Admin Passwords | Hashed storage | SHA256 (legacy) |

### Soft Delete Convention

When querying any soft-deletable entity:
```python
# Always include this filter
.where(Model.deleted_at.is_(None))
```

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

- `UsageAggregate` stores hourly/daily rollups for analytics
- Bucket types: `minute`, `hour`, `day`, `week`, `month`
- Includes cache token tracking (`total_cache_write_tokens`, `total_cache_read_tokens`)
- Cost breakdown by token type (input, output, cache_write, cache_read)

## Budget Management

### Monthly Budget Enforcement

| Aspect | Specification |
|--------|---------------|
| Scope | Per-user monthly limit in USD |
| Timezone | KST (UTC+9) - resets on 1st of each month |
| Enforcement | Bedrock fallback requests blocked when exceeded |
| Fail-open | Budget check failures allow requests by default |
| Cache TTL | 60 seconds (configurable via `PROXY_BUDGET_CACHE_TTL`) |

### Budget Check Response (429)

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

- Pricing loaded from `PROXY_MODEL_PRICING` environment variable (JSON)
- Supports per-region, per-model pricing
- Runtime reload via `POST /api/pricing/reload`
- Cost calculated with 6 decimal precision

### Cost Calculation Formula

```
cost = (tokens / 1,000,000) * price_per_million
```

Token types: `input`, `output`, `cache_write`, `cache_read`

## Cost Model Context

The proxy optimizes costs by:
1. Using Anthropic Plan API as primary (typically lower cost)
2. Auto-fallback to Bedrock PAYG only when rate-limited
3. Tracking all usage for cost visibility and capacity planning
4. Per-user budget limits to prevent unexpected costs
