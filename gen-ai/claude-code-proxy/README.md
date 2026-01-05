# Claude Code Proxy

A proxy service that enables organizations to centrally manage and monitor Claude Code usage with automatic failover to Amazon Bedrock.

## Why Claude Code Proxy?

Claude Code offers two pricing models: a fixed monthly subscription (Plan) or pay-as-you-go via Amazon Bedrock. This proxy helps organizations leverage the best of both worlds.

### Cost Optimization
- **Pay-per-use pricing**: No upfront commitment or bulk subscription required — pay only for what you use via Amazon Bedrock
- **Flexible fallback**: Use Anthropic Plan as primary, automatically switch to Bedrock when rate-limited
- **Usage visibility**: Track token consumption per user with detailed analytics
- **Budget control**: Set monthly spending limits per user to prevent unexpected costs

### Enterprise Security & Compliance
- **Data privacy**: When using Amazon Bedrock, your data is never used for model training
- **Centralized access control**: Manage authentication and permissions through Bedrock API keys
- **Access key handling**: Access keys are stored as HMAC-SHA256 hashes and shown once on issuance
- **Audit logging**: CloudTrail integration enables API call history logging and analysis
- **LLM Gateway**: Centralized governance and policy management for AI usage across the organization

### Operational Benefits
- **Rate limit resilience**: Automatic failover prevents developer workflow interruptions
- **Multi-tenant support**: Issue unique access keys per user or team
- **Admin dashboard**: Web UI for user management, key provisioning, and usage monitoring

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
2. The proxy forwards requests to Anthropic Plan API
3. If Anthropic returns a rate limit error, the proxy automatically retries via Amazon Bedrock
4. All usage is tracked and stored for analytics

## For End Users

1. Get an access key from your admin
2. Configure Claude Code:

### Option 1: Environment Variables
```bash
export ANTHROPIC_BASE_URL=https://proxy.example.com/ak/ak_your_access_key
```

### Option 2: Settings File (`~/.claude/settings.json`)
You can also configure Claude Code globally by editing `~/.claude/settings.json`:
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://proxy.example.com/ak/ak_your_access_key"
  }
}
```

3. Use Claude Code as normal — the proxy handles routing transparently

## For Administrators

### Quick Start (Local Development)

1. Start the database:
```bash
docker-compose up -d db
```

2. Configure backend environment (`backend/.env`):
```bash
cp backend/.env.example backend/.env
```
Update values as needed:
```env
PROXY_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/proxy
PROXY_KEY_HASHER_SECRET=your-secret-key
PROXY_JWT_SECRET=your-jwt-secret
PROXY_ADMIN_USERNAME=admin
PROXY_ADMIN_PASSWORD_HASH=<sha256-hash-of-password>
```
To set a custom admin password, generate a SHA256 hash:
```bash
python - <<'PY'
import hashlib
import getpass

password = getpass.getpass("Admin password: ")
print(hashlib.sha256(password.encode()).hexdigest())
PY
```

3. Run migrations and start the backend:
```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn src.main:app --reload --port 8000
```

4. Start the frontend:
```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

5. Open http://localhost:5173 and login with admin credentials

### Admin Dashboard Features

- Token overview dashboard with throughput, cumulative usage, and top users
- Cost visibility dashboard with total cost, cache cost, model breakdown, and cost trend (KST-based ranges)
- Create users and issue access keys (keys are shown once on creation)
- Register Bedrock credentials per access key and see linked status in the list
- User budget management with real-time usage tracking

### User Budget Management

Set monthly spending limits per user to control Bedrock costs:

- **Monthly Budget**: Set a USD limit per user (e.g., $50/month). Leave empty for unlimited.
- **Automatic Enforcement**: When budget is exceeded, Bedrock fallback requests are blocked with a 429 response
- **Real-time Tracking**: View current usage, remaining budget, and usage percentage in the dashboard
- **KST-based Cycle**: Monthly budget resets on the 1st of each month (Korea Standard Time, UTC+9)

Budget enforcement only applies to Bedrock fallback requests. Anthropic Plan API requests are not affected by user budgets.

Example budget response when exceeded:
```json
{
  "type": "error",
  "error": {
    "type": "rate_limit_error",
    "message": "Monthly budget exceeded: $50.00 used of $50.00 budget"
  }
}
```

### Cost Visibility & Pricing

- Costs are calculated on request completion and stored with a pricing snapshot (non-retroactive).
- Usage filters accept `period=day|week|month` or `start_date/end_date` (YYYY-MM-DD) in KST (UTC+9). Week starts on Sunday.
- Pricing can be updated via `PROXY_MODEL_PRICING` and reloaded with `POST /api/pricing/reload`.

Example `PROXY_MODEL_PRICING`:
```json
{
  "ap-northeast-2": {
    "claude-opus-4-5": {
      "input_price_per_million": "5.00",
      "output_price_per_million": "25.00",
      "cache_write_price_per_million": "6.25",
      "cache_read_price_per_million": "0.50",
      "effective_date": "2025-01-01"
    },
    "claude-sonnet-4-5": {
      "input_price_per_million": "3.00",
      "output_price_per_million": "15.00",
      "cache_write_price_per_million": "3.75",
      "cache_read_price_per_million": "0.30",
      "effective_date": "2025-01-01"
    },
    "claude-haiku-4-5": {
      "input_price_per_million": "1.00",
      "output_price_per_million": "5.00",
      "cache_write_price_per_million": "1.25",
      "cache_read_price_per_million": "0.10",
      "effective_date": "2025-01-01"
    }
  }
}
```

## Deployment

### Using Docker Compose

```bash
docker-compose up -d
```

### AWS Deployment (CDK)

The `infra/` directory contains AWS CDK stacks for production deployment:

```bash
cd infra
pip install -r requirements.txt
cdk deploy --all
```

This deploys:
- VPC with public/private subnets
- RDS PostgreSQL database
- ECS Fargate service for the backend
- CloudFront distribution for secure access
- Secrets Manager for sensitive configuration

### Frontend Deployment (Amplify)

Option A — CLI script (recommended):
```bash
cd frontend
npm ci
npm run deploy:amplify:init
```

Option B — Manual upload via Amplify Console:
1. Build: `npm run build:zip`
2. Upload `dist.zip` in Amplify Console
3. Configure rewrite rule: `</^[^.]+$|\.(?!(js|css|ico|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot|json|map)$)([^.]+$)/>` → `/index.html` (200 Rewrite)

## Configuration Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `PROXY_DATABASE_URL` | Yes | PostgreSQL connection string |
| `PROXY_KEY_HASHER_SECRET` | Yes | Secret for hashing access keys |
| `PROXY_JWT_SECRET` | Yes | Secret for JWT token signing |
| `PROXY_ADMIN_USERNAME` | Yes | Admin login username |
| `PROXY_ADMIN_PASSWORD_HASH` | Yes | SHA256 hash of admin password |
| `PROXY_PLAN_API_KEY` | No | Default Anthropic API key |
| `PROXY_BEDROCK_DEFAULT_MODEL` | No | Default Bedrock model ID |
| `PROXY_BEDROCK_REGION` | No | AWS region for Bedrock (default: ap-northeast-2) |
| `PROXY_MODEL_PRICING` | No | JSON pricing config for cost visibility (per region/model) |
| `PROXY_LOCAL_ENCRYPTION_KEY` | No | 32-byte key for local dev encryption (KMS fallback) |
| `PROXY_CIRCUIT_FAILURE_THRESHOLD` | No | Failures before circuit opens (default: 3) |
| `PROXY_CIRCUIT_RESET_TIMEOUT` | No | Circuit reset timeout in seconds (default: 1800) |

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL
- **Frontend**: React 18, Vite, Tailwind CSS
- **Infrastructure**: AWS CDK, ECS Fargate, RDS, CloudFront

## License

MIT
