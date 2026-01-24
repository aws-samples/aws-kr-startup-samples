# Claude Code Proxy

A proxy service that enables organizations to centrally manage and monitor Claude Code usage with automatic failover to Amazon Bedrock.

<img src="./assets/admin-dashboard.gif" alt="admin-dashboard">

## Why Claude Code Proxy?

Claude Code Proxy is an enterprise LLM gateway that sits between Claude Code clients and AI providers (Anthropic Plan API / Amazon Bedrock).

| Benefit | Description |
|---------|-------------|
| **Cost Optimization** | Pay-per-use via Bedrock, no upfront commitment. Set monthly budgets per user. |
| **Rate Limit Resilience** | Automatic failover to Bedrock when Plan API is rate-limited. |
| **Enterprise Security** | Bedrock data never used for training. Access keys hashed with HMAC-SHA256. |
| **Centralized Control** | Admin dashboard for user management, key provisioning, and usage analytics. |

## How It Works

```
┌─────────────────┐     ┌─────────────────────────────────────────────────┐
│   Claude Code   │     │              Claude Code Proxy                  │
│    (Client)     │     │                                                 │
│                 │     │  ┌─────────┐    ┌──────────────────────────┐    │
│  ANTHROPIC_     │────▶│  │  Proxy  │───▶│   Anthropic Plan API     │    │
│  BASE_URL=      │     │  │  Router │    │   (Primary)              │    │
│  proxy.example  │     │  │         │    └──────────────────────────┘    │
│  .com/ak/...    │     │  │         │              │                     │
│                 │     │  │         │        rate limited?               │
└─────────────────┘     │  │         │              │                     │
                        │  │         │              ▼                     │
                        │  │         │    ┌──────────────────────────┐    │
                        │  │         │───▶│   Amazon Bedrock         │    │
                        │  │         │    │   (Fallback)             │    │
                        │  └─────────┘    └──────────────────────────┘    │
                        │       │                                         │
                        │       ▼                                         │
                        │  ┌─────────┐    ┌──────────────────────────┐    │
                        │  │  Usage  │───▶│   PostgreSQL             │    │
                        │  │ Tracker │    │   (Metrics Storage)      │    │
                        │  └─────────┘    └──────────────────────────┘    │
                        └─────────────────────────────────────────────────┘
```

1. Claude Code sends requests to the proxy instead of directly to Anthropic
2. The proxy forwards requests to Anthropic Plan API (primary)
3. If rate-limited, the proxy automatically retries via Amazon Bedrock
4. All usage is tracked and stored for analytics

---

## Quick Start

Get the proxy running locally in 5 minutes.

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker | 20.10+ |

### 1. Start Database

```bash
docker compose up -d db
```

### 2. Setup Backend

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env
```

Edit `backend/.env` with minimal settings for local development:

```env
PROXY_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/proxy
PROXY_KEY_HASHER_SECRET=local-dev-secret-change-in-prod
PROXY_JWT_SECRET=local-jwt-secret-change-in-prod
PROXY_ADMIN_USERNAME=admin
PROXY_ADMIN_PASSWORD_HASH=<your-bcrypt-hash>
```

Generate admin password hash:

```bash
# Using Python
python -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt()).decode())"

# Or using htpasswd (if available)
htpasswd -nbBC 10 "" your-password | tr -d ':\n'
```

Run migrations and start:

```bash
alembic upgrade head
uvicorn src.main:app --reload --port 8000
```

### 3. Setup Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

### 4. Access Dashboard

Open http://localhost:5173 and login with your admin credentials.

---

## For End Users

Get an access key from your administrator, then configure Claude Code:

### ⚠️ IMPORTANT: ANTHROPIC_AUTH_TOKEN Configuration

**Your routing strategy determines how to set `ANTHROPIC_AUTH_TOKEN`:**

| Routing Strategy | `ANTHROPIC_AUTH_TOKEN` | Why? |
|------------------|------------------------|------|
| **plan_first** (default) | **DO NOT SET** or leave empty | Proxy uses Plan API credentials internally |
| **bedrock_only** | **Set to any non-empty value** | Required for Claude Code authentication |

> **Wrong configuration = requests fail!** Check your routing strategy with your administrator.

### Option 1: Shell Environment (Recommended)

Add to `~/.bashrc` or `~/.zshrc`:

**For plan_first users (default):**
```bash
# DO NOT set ANTHROPIC_AUTH_TOKEN
export ANTHROPIC_BASE_URL="https://proxy.example.com/ak/ak_your_access_key"
```

**For bedrock_only users:**
```bash
export ANTHROPIC_AUTH_TOKEN="any-non-empty-value"
export ANTHROPIC_BASE_URL="https://proxy.example.com/ak/ak_your_access_key"
```

Then reload: `source ~/.bashrc`

> **Why recommended?** Claude Code checks authentication before loading config files. Shell variables ensure the proxy is used from startup.

### Option 2: Settings File

Edit `~/.claude/settings.json`:

**For plan_first users (default):**
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://proxy.example.com/ak/ak_your_access_key"
  }
}
```

**For bedrock_only users:**
```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "any-non-empty-value",
    "ANTHROPIC_BASE_URL": "https://proxy.example.com/ak/ak_your_access_key"
  }
}
```

### Token Limits (Optional)

Control token usage with these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | 16000 | Max tokens for model responses |
| `MAX_THINKING_TOKENS` | 10000 | Budget for Extended Thinking |

---

## For Administrators

### Admin Dashboard

<p align="center">
  <img src="./assets/user-detail.gif" alt="user-detail" width="600">
</p>

| Feature | Description |
|---------|-------------|
| **User Management** | Create users, issue access keys (shown once on creation) |
| **Bedrock Credentials** | Register AWS credentials per access key |
| **Budget Control** | Set monthly USD limits per user |
| **Usage Analytics** | Token throughput, cost breakdown by provider (Plan/Bedrock), top users |

### Routing Strategy

Configure per user in the dashboard:

| Strategy | Behavior |
|----------|----------|
| `plan_first` (default) | Anthropic Plan API first, Bedrock on rate limit |
| `bedrock_only` | Always use Bedrock (no Plan API) |

### Budget Management

- Set monthly USD limit per user (e.g., $50/month)
- Budget exceeded → 429 response, Bedrock requests blocked
- Resets on 1st of each month (KST, UTC+9)
- **Note**: Budget applies only to Bedrock requests

### Cache Control (Bedrock)

Prompt caching is supported when using Bedrock. Add `cache_control` to your messages:

```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Long context...", "cache_control": {"type": "ephemeral"}}
      ]
    }
  ]
}
```

- Maximum 4 cache points per request
- Cache tokens tracked in usage analytics (`cache_read_input_tokens`, `cache_creation_input_tokens`)

### Model Mapping

When new Claude models are released, map them to Bedrock model IDs:

**Via Environment Variable:**

```bash
PROXY_BEDROCK_MODEL_MAPPING='{"claude-sonnet-4-20250514":"apac.anthropic.claude-sonnet-4-20250514-v1:0"}'
```

**Via Admin Dashboard:** Navigate to Model section to add mappings.

> See [Amazon Bedrock Supported Models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html) for Bedrock model IDs.

---

## For Developers

### Project Structure

```
├── backend/          # FastAPI + SQLAlchemy
├── frontend/         # React + Vite + Tailwind
└── infra/            # AWS CDK stacks
```

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend type check
cd frontend
npx tsc --noEmit
```

### Linting

```bash
# Backend
cd backend
ruff check . && ruff format . && mypy src

# Frontend
cd frontend
npm run lint
```

### Database Migrations

```bash
cd backend

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

### API Documentation

Start the backend and visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Deployment

### AWS Deployment (CDK)

Additional requirements for deployment:

| Requirement | Notes |
|-------------|-------|
| AWS CLI 2.0+ | Configured with appropriate credentials |
| AWS CDK 2.0+ | `npm install -g aws-cdk` |

Required AWS permissions: VPC, ECS, RDS, Secrets Manager, KMS, CloudFront, Amplify.

```bash
cd infra
pip install -r requirements.txt
cdk bootstrap  # First time only
cdk deploy --all
```

This deploys:
- VPC with public/private subnets
- RDS PostgreSQL with SSL
- ECS Fargate service
- CloudFront distribution
- Secrets Manager for configuration

### Frontend Deployment (Amplify)

**Option A: Bootstrap Script (Recommended)**

```bash
cd frontend
npm ci
echo "VITE_BACKEND_API_URL=https://<your-cloudfront-domain>" > .env.local
./scripts/amplify-bootstrap-deploy.sh
```

**Option B: Manual Upload**

1. Build: `npm run build:zip`
2. Upload `dist.zip` in Amplify Console
3. Add SPA rewrite rule: `</^[^.]+$|\.(?!(js|css|ico|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot|json|map)$)([^.]+$)/>` → `/index.html` (200)

---

## Configuration Reference

### Required Variables

| Variable | Description |
|----------|-------------|
| `PROXY_DATABASE_URL` | PostgreSQL connection string |
| `PROXY_KEY_HASHER_SECRET` | Secret for hashing access keys |
| `PROXY_JWT_SECRET` | Secret for JWT token signing |
| `PROXY_ADMIN_USERNAME` | Admin login username |
| `PROXY_ADMIN_PASSWORD_HASH` | Bcrypt hash of admin password |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXY_PLAN_API_KEY` | - | Default Anthropic API key |
| `PROXY_BEDROCK_REGION` | ap-northeast-2 | AWS region for Bedrock |
| `PROXY_BEDROCK_DEFAULT_MODEL` | - | Default Bedrock model ID |
| `PROXY_BEDROCK_MODEL_MAPPING` | - | JSON mapping of model IDs |
| `PROXY_MODEL_PRICING` | - | JSON pricing config (per region/model) |
| `PROXY_CIRCUIT_FAILURE_THRESHOLD` | 3 | Failures before circuit opens |
| `PROXY_CIRCUIT_RESET_TIMEOUT` | 1800 | Circuit reset timeout (seconds) |
| `PROXY_LOCAL_ENCRYPTION_KEY` | - | 32-byte key for local dev (KMS fallback) |
| `PROXY_LOG_LEVEL` | INFO | Log level (DEBUG, INFO, WARNING, ERROR) |

### Production Variables

| Variable | Description |
|----------|-------------|
| `PROXY_DB_SSL_VERIFY` | Enable SSL verification for RDS |
| `PROXY_DB_CA_BUNDLE` | Path to RDS CA bundle (e.g., `/etc/ssl/certs/rds-ca-bundle.pem`) |

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `Connection refused` on startup | Ensure PostgreSQL is running: `docker compose up -d db` |
| `Invalid access key` | Verify the key format: `ak_` prefix required |
| `Budget exceeded` (429) | Check user budget in admin dashboard |
| `Model not found` | Add model mapping via env var or dashboard |
| **Requests fail with plan_first** | **Remove `ANTHROPIC_AUTH_TOKEN` from your environment** - Plan users should NOT set this variable |
| **Requests fail with bedrock_only** | **Set `ANTHROPIC_AUTH_TOKEN` to any non-empty value** - Bedrock-only users MUST set this variable |

### Logs

```bash
# Backend logs (local)
uvicorn src.main:app --reload --log-level debug

# ECS logs (production)
aws logs tail /ecs/claude-code-proxy --follow

# ECS container shell (requires execute-command enabled)
aws ecs execute-command --cluster <cluster-name> --task <task-id> \
  --container backend --interactive --command "/bin/sh"
```

---

## Contributing

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

We welcome contributions! Here's how you can help:

- **Bug Reports**: Open an issue with reproduction steps
- **Feature Requests**: Open an issue describing the use case
- **Pull Requests**: Fork the repo and submit a PR

Please ensure your code passes linting and tests before submitting.

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL |
| Frontend | React 18, Vite, Tailwind CSS |
| Infrastructure | AWS CDK, ECS Fargate, RDS, CloudFront |
