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

## Important Notes

- Access keys are stored hashed with HMAC-SHA256
- Bedrock credentials are encrypted with KMS
- Circuit breaker state is stored in memory (resets on restart)
- All DB operations require `await`
