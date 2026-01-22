---
inclusion: always
---

# Tech Stack & Development Guide

## Stack Overview

| Layer | Technologies |
|-------|-------------|
| Backend | FastAPI 0.109+, Python 3.11+, SQLAlchemy 2.0 (async), PostgreSQL 15, asyncpg |
| Frontend | React 18, Vite 5, TypeScript, Tailwind CSS 3, react-router-dom v6, recharts |
| Infrastructure | AWS CDK (Python), ECS Fargate, Aurora Serverless v2, Amplify, KMS, CloudFront |

## Code Conventions

### Python (Backend)

| Rule | Requirement |
|------|-------------|
| Async operations | **ALWAYS** use `async/await` for ALL database and HTTP operations |
| Type hints | **REQUIRED** on all function signatures |
| Environment variables | **MUST** use `PROXY_` prefix |
| HTTP client | Use `httpx` for async HTTP requests |
| AWS SDK | Use `boto3` for AWS operations |
| Logging | Use `structlog` (structured JSON format) |
| Config | Use `pydantic-settings` with validation |

```python
# CORRECT: Async database operation with type hints
async def get_user(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# INCORRECT: Missing async, missing type hints
def get_user(session, user_id):
    return session.execute(select(User).where(User.id == user_id))
```

### TypeScript (Frontend)

| Rule | Requirement |
|------|-------------|
| Import paths | Use `@/` alias (maps to `src/`) |
| API calls | Centralize in `lib/api.ts` |
| Styling | Tailwind utility classes only (no custom CSS) |

### Database Patterns

| Pattern | Implementation |
|---------|----------------|
| Soft delete | Set `deleted_at` timestamp, **ALWAYS** filter with `.where(Model.deleted_at.is_(None))` |
| Access keys | Store as HMAC-SHA256 hash (**NEVER** plaintext) |
| Bedrock credentials | KMS envelope encryption required |
| All queries | **MUST** be async (`await session.execute(...)`) |

```python
# CORRECT: Soft delete query pattern
query = select(AccessKey).where(
    AccessKey.user_id == user_id,
    AccessKey.deleted_at.is_(None)  # ALWAYS include this filter
)

# INCORRECT: Missing soft delete filter
query = select(AccessKey).where(AccessKey.user_id == user_id)
```

## Essential Commands

```bash
# Backend (from backend/)
pip install -e ".[dev]"           # Install deps
uvicorn src.main:app --reload     # Dev server :8000
alembic upgrade head              # Run migrations
alembic revision --autogenerate -m "desc"  # New migration
pytest                            # Tests
ruff check . && ruff format .     # Lint/format
mypy src                          # Type check

# Frontend (from frontend/)
npm ci                            # Install deps
npm run dev                       # Dev server :5173
npm run build                     # Production build

# Docker
docker-compose up -d              # Full stack
docker-compose up db              # DB only
```

## Environment Variables

### Backend (Required)

| Variable | Purpose |
|----------|---------|
| `PROXY_DATABASE_URL` | PostgreSQL async connection string (format: `postgresql+asyncpg://...`) |
| `PROXY_KEY_HASHER_SECRET` | HMAC salt for access key hashing |
| `PROXY_JWT_SECRET` | Admin JWT signing secret |
| `PROXY_ADMIN_USERNAME` | Admin login username |
| `PROXY_ADMIN_PASSWORD_HASH` | SHA256 hash of admin password |
| `PROXY_LOCAL_ENCRYPTION_KEY` | 32-byte key for local dev (KMS fallback) |

### Backend (Secrets Manager ARNs - Production)

| Variable | Purpose |
|----------|---------|
| `PROXY_DATABASE_URL_ARN` | RDS secret ARN (auto-constructs connection string) |
| `PROXY_KEY_HASHER_SECRET_ARN` | Key hasher secret ARN |
| `PROXY_JWT_SECRET_ARN` | JWT secret ARN |
| `PROXY_ADMIN_CREDENTIALS_ARN` | Admin credentials ARN (JSON: `{"username": "...", "password": "..."}`) |

### Backend (Optional)

| Variable | Default | Purpose |
|----------|---------|---------|
| `PROXY_PLAN_API_KEY` | - | Anthropic API key (required for `plan_first` strategy) |
| `PROXY_BEDROCK_REGION` | `ap-northeast-2` | AWS Bedrock region for fallback |
| `PROXY_BEDROCK_MODEL_MAPPING` | `{}` | JSON map of Claude Code model IDs → Bedrock model IDs |
| `PROXY_BEDROCK_DEFAULT_MODEL` | (deprecated) | Fallback model ID (no longer used; mapping required) |
| `PROXY_CIRCUIT_FAILURE_THRESHOLD` | `3` | Failures before circuit opens (per access key) |
| `PROXY_CIRCUIT_RESET_TIMEOUT` | `1800` | Circuit reset timeout (seconds) |
| `PROXY_MODEL_PRICING` | - | JSON pricing config for cost visibility (per region/model) |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | `4096` | Maximum response tokens (overrides client value) |
| `MAX_THINKING_TOKENS` | `1024` | Maximum Extended Thinking budget tokens |

### Backend (Cache TTLs)

| Variable | Default | Purpose |
|----------|---------|---------|
| `PROXY_ACCESS_KEY_CACHE_TTL` | `60` | Access key cache TTL (seconds) |
| `PROXY_BEDROCK_KEY_CACHE_TTL` | `300` | Bedrock key cache TTL (seconds) |
| `PROXY_BUDGET_CACHE_TTL` | `60` | Budget check cache TTL (seconds) |

### Frontend

| Variable | Purpose |
|----------|---------|
| `VITE_BACKEND_API_URL` | Backend API base URL |

## Database Schema

6 tables: `users`, `access_keys`, `bedrock_keys`, `token_usage`, `usage_aggregates`, `model_mappings`

| Relationship | Cascade Behavior |
|--------------|------------------|
| `access_keys.user_id` → `users.id` | CASCADE |
| `bedrock_keys.access_key_id` → `access_keys.id` | CASCADE |
| `token_usage.access_key_id` → `access_keys.id` | SET NULL |

### Cost Tracking Fields (token_usage)

| Field | Type | Description |
|-------|------|-------------|
| `estimated_cost_usd` | Numeric(12,6) | Total estimated cost |
| `input_cost_usd` | Numeric(12,6) | Input token cost |
| `output_cost_usd` | Numeric(12,6) | Output token cost |
| `cache_write_cost_usd` | Numeric(12,6) | Cache write cost |
| `cache_read_cost_usd` | Numeric(12,6) | Cache read cost |
| `pricing_*` | various | Pricing snapshot at request time |

## Debugging Quick Reference

| Issue | Resolution |
|-------|------------|
| "Access key not found" | Verify `key_hash` matches HMAC of key, check `deleted_at IS NULL` |
| Circuit breaker stuck | In-memory state; restart backend or wait for timeout |
| Bedrock fallback fails | Check `bedrock_keys` entry exists, verify AWS creds, check KMS perms |
| Migration conflict | `alembic downgrade -1`, regenerate, review diff, `alembic upgrade head` |
| Budget not updating | Cache TTL is 60s; wait for expiry or restart backend |
| Pricing not applied | Call `POST /api/pricing/reload` after updating `PROXY_MODEL_PRICING` |
| "Rate limit exceeded" response from Plan | Circuit breaker triggered; check `PROXY_CIRCUIT_FAILURE_THRESHOLD` and `PROXY_CIRCUIT_RESET_TIMEOUT` |
| Extended Thinking not working | Verify `MAX_THINKING_TOKENS` is set, check if model supports thinking, verify budget_tokens in request |

## API Endpoints Reference

### Admin Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/admin/auth/login` | Admin login (Basic auth) |
| GET | `/admin/users` | List users |
| POST | `/admin/users` | Create user |
| GET | `/admin/users/{id}` | Get user |
| DELETE | `/admin/users/{id}` | Delete user |
| GET | `/admin/users/{id}/budget` | Get user budget status |
| PUT | `/admin/users/{id}/budget` | Update user budget |
| PUT | `/admin/users/{id}/routing-strategy` | Update routing strategy |
| GET | `/admin/users/{id}/access-keys` | List access keys |
| POST | `/admin/users/{id}/access-keys` | Create access key |
| DELETE | `/admin/access-keys/{id}` | Revoke access key |
| POST | `/admin/access-keys/{id}/rotate` | Rotate access key |
| POST | `/admin/access-keys/{id}/bedrock-key` | Register Bedrock key |
| GET | `/admin/usage` | Get usage data |
| GET | `/admin/usage/top-users` | Get top users by usage |

### Pricing Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/pricing/models` | Get model pricing |
| POST | `/api/pricing/reload` | Reload pricing config |

## Testing

```bash
# Backend
pytest                           # All tests
pytest --cov=src                 # With coverage
pytest tests/test_file.py -v     # Specific file

# Frontend
npx tsc --noEmit                 # Type check
npm run lint                     # ESLint
```
