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
│   ├── pages/                 # Page components (Dashboard, Users, UserDetail, Login)
│   ├── components/            # Shared components (AdminLayout, PageHeader)
│   ├── lib/
│   │   ├── api.ts             # API client
│   │   └── usageRange.ts      # Date range utilities
│   ├── App.tsx                # Router setup
│   └── main.tsx               # Entry point
├── scripts/                   # Deployment scripts
│   └── amplify-bootstrap-deploy.sh  # Amplify deployment

infra/                          # AWS CDK (Python)
├── stacks/
│   ├── network_stack.py       # VPC, Security Groups
│   ├── secrets_stack.py       # KMS, Secrets Manager
│   ├── database_stack.py      # Aurora Serverless v2
│   ├── compute_stack.py       # ECS Fargate, ALB
│   └── cloudfront_stack.py    # CloudFront distribution
└── app.py                     # CDK entry point
```

## Layered Architecture Rules

```
API Layer → Domain Layer → Repository Layer → Database
```

| Rule | Constraint |
|------|------------|
| Layer isolation | NEVER bypass layers (no direct DB access from API handlers) |
| DB operations | ALL queries MUST go through repositories |
| Business logic | MUST reside in `domain/` or `proxy/`, not in API handlers |
| Dependencies | Inject via FastAPI `Depends()` for testability |

## Design Patterns

### Adapter Pattern (Proxy)
- `AdapterBase` in `proxy/adapter_base.py` defines the interface
- New AI providers MUST implement `AdapterBase`
- Existing: `PlanAdapter` (Anthropic), `BedrockAdapter` (AWS Bedrock)

### Repository Pattern
All DB access MUST use repositories in `backend/src/repositories/`:
- `UserRepository` - User CRUD
- `AccessKeyRepository` - Key management + caching
- `BedrockKeyRepository` - Encrypted credentials
- `UsageRepository` - Usage events and aggregates

## Code Conventions

### Backend (Python)
- `async/await` REQUIRED for all DB and HTTP operations
- Type hints REQUIRED on all function signatures
- Environment variables MUST use `PROXY_` prefix
- Soft delete: set `deleted_at` timestamp, ALWAYS filter with `.where(Model.deleted_at.is_(None))`

### Frontend (TypeScript)
- Import paths: use `@/` alias (maps to `src/`)
- API calls: centralize in `lib/api.ts`
- Routing: react-router-dom v6, page components in `pages/`

### Database
- PostgreSQL 15 + asyncpg (async driver)
- SQLAlchemy 2.0 async mode
- Alembic for migrations
- Tables: `users`, `access_keys`, `bedrock_keys`, `token_usage`, `usage_aggregates`

## Frontend Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/login` | LoginPage | Admin authentication |
| `/dashboard` | DashboardPage | Usage overview, charts |
| `/users` | UsersPage | User list, create user |
| `/users/:id` | UserDetailPage | User detail, access keys, budget |

## Infrastructure Architecture

### CDK Stacks

| Stack | Resources | Purpose |
|-------|-----------|---------|
| NetworkStack | VPC, Security Groups | Network isolation |
| SecretsStack | KMS Key, Secrets Manager | Encryption, credentials |
| DatabaseStack | Aurora Serverless v2 | PostgreSQL 17.4 database |
| ComputeStack | ECS Fargate, ALB | Backend service |
| CloudFrontStack | CloudFront Distribution | Secure admin access |

### Security Pattern: X-Origin-Verify

ALB is protected by a custom header validation pattern:
1. CloudFront adds `X-Origin-Verify` header with secret value
2. ALB listener rule validates header before forwarding
3. Direct ALB access returns 403 Forbidden

Note: CloudFront prefix list (`pl-22a6434b`) exceeds default SG rule limit (~130 rules). To use prefix list instead, increase "Inbound rules per security group" quota to 200+.

### CDK Context Variables

Deploy with optional configuration:
```bash
cdk deploy --context environment=prod --context log_level=DEBUG
```

| Context Variable | Default | Description |
|------------------|---------|-------------|
| `account` | - | AWS account ID |
| `region` | `ap-northeast-2` | AWS region |
| `environment` | `dev` | Deployment environment |
| `log_level` | `INFO` | Log level |
| `plan_api_key` | - | Anthropic API key |
| `bedrock_region` | - | Bedrock region override |
| `bedrock_default_model` | - | Default Bedrock model |

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

| Task | Location |
|------|----------|
| Add API endpoint | `backend/src/api/` → register in `main.py` |
| Modify proxy logic | `backend/src/proxy/router.py` |
| Add/modify DB model | `backend/src/db/models.py` → create Alembic migration |
| Add repository | `backend/src/repositories/` → inject via `Depends()` |
| Modify config | `backend/src/config.py` |
| Add frontend page | `frontend/src/pages/` → update `App.tsx` routes |
| Add CDK stack | `infra/stacks/` → register in `app.py` |

## Adding New Features

1. **New API endpoint**: Create handler in `api/`, add router to `main.py`
2. **New DB table**: Add model in `db/models.py`, run `alembic revision --autogenerate -m "desc"`
3. **New repository**: Implement in `repositories/`, inject via `Depends()`
4. **New AI provider**: Implement `AdapterBase` in `proxy/`
5. **New frontend page**: Add component in `pages/`, update `App.tsx` routes
