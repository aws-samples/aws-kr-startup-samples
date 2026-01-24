# AGENTS.md

Project context document for AI coding agents.

## Project Overview

**Claude Code Proxy** is an enterprise LLM gateway service that manages Claude Code access with automatic failover, usage tracking, and multi-tenant access control. It acts as a centralized proxy between Claude Code clients and AI model providers (Anthropic Plan API and Amazon Bedrock).

### Core Features
- **Dual-provider routing**: Primary Anthropic Plan API with automatic Bedrock fallback on rate limits
- **Multi-tenant access**: Unique access keys per user with per-key budget limits
- **Cost visibility**: Real-time token usage tracking with pricing snapshots and detailed breakdowns
- **Admin dashboard**: Web UI for user management, key provisioning, Bedrock credential registration, and analytics
- **Enterprise security**: Access keys stored as hashed values, Bedrock credentials encrypted with KMS

## Detailed Documentation

For detailed project information, refer to the documents in `.kiro/steering/`:

| File | Contents |
|------|----------|
| `.kiro/steering/product.md` | Product overview, business context, API contract, data model |
| `.kiro/steering/structure.md` | Project structure, architecture patterns, data flow |
| `.kiro/steering/tech.md` | Tech stack, commands, environment variables, debugging guide |

## Quick Reference

### Local Bootstrap

```bash
# Full stack (docker compose)
docker compose up --build

# DB only (when running backend/frontend locally)
docker compose up db
```

### Build & Run

```bash
# Backend
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn src.main:app --reload --port 8000

# Frontend
cd frontend
npm ci
npm run dev

# Infrastructure
cd infra
pip install -r requirements.txt
cdk synth
```

### Environment Variables

Backend (e.g., `.env` or runtime environment):
- Copy `backend/.env.example` to `backend/.env` and update values.
- `PROXY_DATABASE_URL` e.g., `postgresql+asyncpg://postgres:postgres@localhost:5432/proxy`
- `PROXY_PLAN_API_KEY` (optional)
- `PROXY_KEY_HASHER_SECRET`
- `PROXY_ADMIN_USERNAME`
- `PROXY_ADMIN_PASSWORD_HASH`

Frontend:
- Copy `frontend/.env.example` to `frontend/.env.local` (or `frontend/.env`) and update values.
- `VITE_BACKEND_API_URL` e.g., `http://localhost:8000`

Note: See `docker-compose.yml` for default values/examples

### Infrastructure Prerequisites

- AWS credentials/region configuration required, see `.kiro/steering/tech.md` for details

### Testing

```bash
# Backend tests
cd backend
pytest

# Frontend type check
cd frontend
npx tsc --noEmit
```

### Linting & Formatting

```bash
# Backend
cd backend
ruff check .
ruff format .
mypy src

# Frontend
cd frontend
npm run lint
```

## Code Style

### Backend (Python)
- Python 3.11+, type hints required
- Use async/await pattern (all DB/HTTP operations)
- Environment variables use `PROXY_` prefix
- Repository pattern for DB access separation

### Frontend (TypeScript)
- React 18 + Vite
- Path alias: `@/` → `src/`
- Tailwind CSS
- No Node version pinning file (`.nvmrc`/`.node-version`)

## Main Endpoint

```
POST /ak/{access_key}/v1/messages  # Main proxy endpoint
```

## Database

- PostgreSQL 15 + asyncpg
- Migrations: Alembic
- Soft delete pattern (`deleted_at` column)

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## Key File Locations

| Area | File |
|------|------|
| FastAPI app | `backend/src/main.py` |
| Proxy router | `backend/src/api/proxy_router.py` |
| Routing logic | `backend/src/proxy/router.py` |
| DB models | `backend/src/db/models.py` |
| Config | `backend/src/config.py` |
| Logging | `backend/src/logging.py` |
| API client | `frontend/src/lib/api.ts` |
| CDK app | `infra/app.py` |

## Architecture Overview

### Routing Strategies

Users can configure one of two routing strategies:

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| `plan_first` (default) | Try Anthropic Plan API first, fallback to Bedrock on rate limit/failure | Organizations with existing Plan subscription |
| `bedrock_only` | Skip Plan API entirely, use only Bedrock | Pure pay-per-use model |

Configure via: Admin dashboard or `PUT /admin/users/{user_id}/routing-strategy`

### Request Flow Architecture

```
POST /ak/{access_key}/v1/messages
    ├─ AuthService (validate & cache access key)
    ├─ BudgetService (KST-based monthly budget check)
    ├─ ProxyRouter (circuit breaker + routing strategy)
    │   ├─ PlanAdapter (primary: Anthropic Plan API)
    │   │   ├─ stream response to client
    │   │   └─ UsageRecorder (track tokens & calculate cost)
    │   │
    │   └─ [ON RATE LIMIT/FAILURE]
    │       └─ BedrockAdapter (fallback: AWS Bedrock Converse)
    │           ├─ request format conversion
    │           ├─ stream response to client
    │           └─ UsageRecorder (track tokens & calculate cost)
    │
    └─ Return response to Claude Code client
```

### Core Components

**Proxy Layer** (`backend/src/proxy/`)
- `router.py` - ProxyRouter: Routes requests based on strategy, manages fallback & circuit breaker
- `plan_adapter.py` - PlanAdapter: Wraps Anthropic Plan API with error handling
- `bedrock_adapter.py` - BedrockAdapter: Wraps Bedrock Converse API with format conversion
- `budget.py` - BudgetService: Enforces monthly budget limits (KST timezone)
- `auth.py` - AuthService: Access key authentication with caching (60s TTL)
- `circuit_breaker.py` - CircuitBreaker: Per-key failure tracking and recovery
- `usage.py` - UsageRecorder: Tracks tokens and calculates costs with pricing snapshots
- `streaming_usage.py` - StreamingUsageCollector: Collects usage from SSE streams
- `bedrock_converse/` - Format conversion utilities for Bedrock API (including cache control)

**Admin API** (`backend/src/api/`)
- `admin_auth.py` - JWT-based admin authentication
- `admin_users.py` - User management endpoints
- `admin_keys.py` - Access key provisioning and rotation
- `admin_bedrock_keys.py` - Bedrock credential registration (encrypted with KMS)
- `admin_usage.py` - Usage aggregation and cost breakdown
- `admin_models.py` - Model mapping management

**Data Layer** (`backend/src/db/` & `backend/src/repositories/`)
- SQLAlchemy ORM models with async support
- Repository pattern for data access separation
- Soft delete pattern for audit trails
- HMAC-SHA256 key hashing (keys never stored plaintext)
- KMS-encrypted Bedrock credentials

**Frontend** (`frontend/src/`)
- Dashboard with token throughput and cost visibility
- User management interface
- Access key provisioning with copy-to-clipboard
- Bedrock credential linking
- Budget monitoring and usage tracking
- Model mapping configuration

### Key Architectural Patterns

| Pattern | Usage |
|---------|-------|
| Adapter Pattern | Provider abstraction (Plan vs Bedrock) |
| Repository Pattern | Data access separation via repositories |
| Circuit Breaker | Rate limit resilience with per-key state |
| Multi-level Caching | Auth keys (60s), Bedrock keys (300s), budgets (60s) |
| Streaming | SSE support with token counting during streaming |
| Soft Deletes | `deleted_at` columns for audit compliance |
| Structured Logging | JSON logs via structlog (configurable via `PROXY_LOG_LEVEL`) |

### Adapters

- **PlanAdapter** - Anthropic Plan API client
  - Streaming and non-streaming request support
  - Error mapping to Anthropic error types
  - Failure triggers circuit breaker

- **BedrockAdapter** - AWS Bedrock Converse API client
  - Converts Claude Code request format to Bedrock format
  - Handles Extended Thinking (budget_tokens normalization)
  - Supports cache control (max 4 cache points per request)
  - Streaming usage collection during response
  - Error mapping and rate limit detection

- **ModelMapping** - Dynamic model ID resolution
  - Configured via environment or admin UI
  - Supports per-region Bedrock model IDs
  - Fallback to default if no mapping exists

### Budget Management

- Per-user monthly budget limits (USD)
- Enforced only on Bedrock fallback requests
- KST-based monthly cycle (resets on 1st of each month)
- Budget exceeded → 429 response with reset date

### Cost Visibility

- Token usage tracked per request with pricing snapshot
- Cost breakdown: input, output, cache read, cache write
- Provider-aware tracking: `plan` (Anthropic Plan API) and `bedrock` (AWS Bedrock)
- Pricing config via `PROXY_MODEL_PRICING` (JSON, per region/model)
- Usage filters: `period=day|week|month` or `start_date/end_date` (KST)
- Filter by provider: `?provider=plan` or `?provider=bedrock`

## Admin API Endpoints

```
# Users
POST   /admin/users
GET    /admin/users/{user_id}
PUT    /admin/users/{user_id}/routing-strategy
PUT    /admin/users/{user_id}/budget
GET    /admin/users/{user_id}/budget

# Access Keys
POST   /admin/keys
GET    /admin/keys/{key_id}
DELETE /admin/keys/{key_id}

# Bedrock Keys
POST   /admin/bedrock-keys
PUT    /admin/bedrock-keys/{access_key_id}

# Usage & Cost
GET    /admin/usage/aggregate
GET    /admin/usage/cost-breakdown
```

## Testing

### Test Structure

```
backend/tests/
├── test_bedrock_adapter.py       # BedrockAdapter unit tests
├── test_bedrock_converse.py      # Bedrock format conversion
├── test_proxy_router.py          # ProxyRouter routing logic
├── test_budget_service.py        # Budget enforcement
├── test_usage_recorder.py        # Usage tracking
└── test_admin_*.py               # Admin API endpoints
```

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_bedrock_adapter.py -v

# With coverage
pytest --cov=src --cov-report=html
```

## Important Notes

- Access keys are stored hashed with HMAC-SHA256
- Bedrock credentials are encrypted with KMS (or local key for dev)
- Circuit breaker state is stored in memory (resets on restart)
- All DB operations require `await`
- Budget enforcement applies only to Bedrock requests
- Pricing snapshots are non-retroactive (stored per request)
- Logs are JSON-formatted via structlog for production observability
- ECS execute-command is enabled for container debugging
