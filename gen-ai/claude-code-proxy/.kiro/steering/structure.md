---
inclusion: always
---

# Project Structure & Architecture

## Directory Layout

```
backend/                        # FastAPI backend (Python 3.11+)
├── src/
│   ├── api/                   # Route handlers (admin_*.py, proxy_router.py, deps.py)
│   ├── db/                    # Database layer (models.py, session.py)
│   ├── domain/                # Business logic (entities.py, enums.py, schemas.py, pricing.py, cost_calculator.py)
│   ├── proxy/                 # Proxy routing (adapters, circuit_breaker.py, router.py, budget.py)
│   │   └── bedrock_converse/  # Bedrock API translation
│   ├── repositories/          # Data access layer
│   ├── security/              # Encryption & keys
│   ├── config.py              # Settings (pydantic-settings)
│   └── main.py                # App entry point
├── alembic/versions/          # DB migrations
└── tests/                     # pytest tests

frontend/                       # React admin dashboard (TypeScript)
├── src/
│   ├── pages/                 # Page components
│   ├── components/            # Shared components
│   ├── lib/                   # API client, utilities
│   ├── App.tsx                # Router setup
│   └── main.tsx               # Entry point

infra/                          # AWS CDK (Python)
├── stacks/                    # CDK stack definitions
└── app.py                     # CDK entry point
```

## Architecture Rules

### Layer Hierarchy (MUST follow)

```
API Layer → Domain Layer → Repository Layer → Database
```

- NEVER bypass layers (no direct DB access from API handlers)
- ALL DB queries MUST go through repositories
- Business logic MUST reside in `domain/` or `proxy/`, NOT in API handlers
- Inject dependencies via FastAPI `Depends()` for testability

### Design Patterns

**Adapter Pattern (Proxy)**
- `AdapterBase` in `proxy/adapter_base.py` defines the interface
- New AI providers MUST implement `AdapterBase`
- Existing adapters: `PlanAdapter` (Anthropic), `BedrockAdapter` (AWS Bedrock)

**Repository Pattern**
- `UserRepository` - User CRUD
- `AccessKeyRepository` - Key management + caching
- `BedrockKeyRepository` - Encrypted credentials
- `UsageRepository` - Usage events and aggregates
- `ModelMappingRepository` - Model ID mappings

## Code Conventions

### Backend (Python) - CRITICAL

```python
# REQUIRED: async/await for ALL DB and HTTP operations
async def get_user(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# REQUIRED: Type hints on ALL function signatures
# REQUIRED: Environment variables use PROXY_ prefix
# REQUIRED: Soft delete filter on ALL queries for soft-deletable entities
query = select(AccessKey).where(
    AccessKey.user_id == user_id,
    AccessKey.deleted_at.is_(None)  # ALWAYS include this
)
```

### Frontend (TypeScript)

- Import paths: use `@/` alias (maps to `src/`)
- API calls: centralize in `lib/api.ts`
- Routing: react-router-dom v6, page components in `pages/`
- Styling: Tailwind utility classes only

### Database

- PostgreSQL 15 + asyncpg (async driver)
- SQLAlchemy 2.0 async mode
- Alembic for migrations
- Tables: `users`, `access_keys`, `bedrock_keys`, `token_usage`, `usage_aggregates`, `model_mappings`

## Frontend Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/login` | LoginPage | Admin authentication |
| `/dashboard` | DashboardPage | Usage overview, charts |
| `/users` | UsersPage | User list, create user |
| `/users/:id` | UserDetailPage | User detail, access keys, budget |

## Request Flow

```
POST /ak/{access_key}/v1/messages
    → proxy_router.py (auth via access key)
    → router.py (circuit breaker check)
    → PlanAdapter (primary) or BedrockAdapter (fallback)
    → usage.py (record tokens)
    → stream response to client
```

## File Location Guide

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `backend/src/api/` | Register router in `main.py` |
| Modify proxy logic | `backend/src/proxy/router.py` | |
| Add/modify DB model | `backend/src/db/models.py` | Create Alembic migration after |
| Add repository | `backend/src/repositories/` | Inject via `Depends()` |
| Modify config | `backend/src/config.py` | Use `PROXY_` prefix for env vars |
| Add frontend page | `frontend/src/pages/` | Update `App.tsx` routes |
| Add CDK stack | `infra/stacks/` | Register in `app.py` |

## Adding New Features

1. **New API endpoint**: Create handler in `api/`, add router to `main.py`
2. **New DB table**: Add model in `db/models.py`, run `alembic revision --autogenerate -m "desc"`
3. **New repository**: Implement in `repositories/`, inject via `Depends()`
4. **New AI provider**: Implement `AdapterBase` in `proxy/`
5. **New frontend page**: Add component in `pages/`, update `App.tsx` routes

## Infrastructure

### CDK Stacks

| Stack | Purpose |
|-------|---------|
| NetworkStack | VPC, Security Groups |
| SecretsStack | KMS Key, Secrets Manager |
| DatabaseStack | Aurora Serverless v2 (PostgreSQL 17.4) |
| ComputeStack | ECS Fargate, ALB |
| CloudFrontStack | CloudFront distribution |

### Security: X-Origin-Verify Pattern

ALB protected by custom header validation:
1. CloudFront adds `X-Origin-Verify` header with secret
2. ALB validates header before forwarding
3. Direct ALB access returns 403

### CDK Context Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `account` | - | AWS account ID |
| `region` | `ap-northeast-2` | AWS region |
| `environment` | `dev` | Deployment environment |
| `log_level` | `INFO` | Log level |
