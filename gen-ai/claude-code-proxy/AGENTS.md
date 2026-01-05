# AGENTS.md

Project context document for AI coding agents.

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
| API client | `frontend/src/lib/api.ts` |
| CDK app | `infra/app.py` |

## Architecture Overview

### Routing Strategies

Users can configure one of two routing strategies:

| Strategy | Behavior |
|----------|----------|
| `plan_first` (default) | Try Anthropic Plan API first, fallback to Bedrock on rate limit |
| `bedrock_only` | Skip Plan API entirely, use only Bedrock |

Configure via: `PUT /admin/users/{user_id}/routing-strategy`

### Adapters

- `PlanAdapter` (`backend/src/proxy/plan_adapter.py`): Anthropic Plan API client
- `BedrockAdapter` (`backend/src/proxy/bedrock_adapter.py`): Bedrock Converse API client
- `ProxyRouter` (`backend/src/proxy/router.py`): Routes requests based on strategy

### Budget Management

- Per-user monthly budget limits (USD)
- Enforced only on Bedrock fallback requests
- KST-based monthly cycle (resets on 1st of each month)
- Budget exceeded → 429 response with reset date

### Cost Visibility

- Token usage tracked per request with pricing snapshot
- Cost breakdown: input, output, cache read, cache write
- Pricing config via `PROXY_MODEL_PRICING` (JSON, per region/model)
- Usage filters: `period=day|week|month` or `start_date/end_date` (KST)

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
