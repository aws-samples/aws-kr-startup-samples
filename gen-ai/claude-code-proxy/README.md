# Claude Code Proxy

A proxy service that enables organizations to centrally manage and monitor Claude Code usage through Amazon Bedrock.

<img src="./assets/admin-dashboard.gif" alt="admin-dashboard">

## Why Claude Code Proxy?

Claude Code Proxy is an enterprise LLM gateway that sits between Claude Code clients and Amazon Bedrock.

| Benefit | Description |
|---------|-------------|
| **Cost Optimization** | Pay-per-use via Bedrock, no upfront commitment. Set monthly budgets per user. |
| **Enterprise Security** | Bedrock data never used for training. Access keys hashed with HMAC-SHA256. |
| **SSO Integration** | AWS SSO login → automatic user provisioning and access key issuance. |
| **Centralized Control** | Admin dashboard for user management, group policies, and usage analytics. |

## How It Works

```
┌─────────────────┐     ┌─────────────────────────────────────────────────┐
│   Claude Code   │     │              Claude Code Proxy                  │
│    (Client)     │     │                                                 │
│                 │     │  ┌─────────┐    ┌──────────────────────────┐    │
│  ANTHROPIC_     │────▶│  │  Auth   │───▶│   Amazon Bedrock         │    │
│  BASE_URL=      │     │  │  + Proxy│    │   (via ECS Task Role)    │    │
│  proxy-apigw    │     │  │         │    └──────────────────────────┘    │
│                 │     │  └─────────┘                                    │
│  apiKeyHelper   │     │       │                                         │
│  (SSO → token)  │     │       ▼                                         │
│                 │     │  ┌─────────┐    ┌──────────────────────────┐    │
└─────────────────┘     │  │  Usage  │───▶│   PostgreSQL             │    │
                        │  │ Tracker │    │   (Metrics Storage)      │    │
                        │  └─────────┘    └──────────────────────────┘    │
                        └─────────────────────────────────────────────────┘
```

1. User runs `aws sso login`, then starts Claude Code
2. `apiKeyHelper` script calls `/auth/sso` with SigV4 → proxy issues an access key
3. Claude Code sends requests to the proxy with the access key
4. Proxy authenticates the user, calls Bedrock via ECS task role IAM
5. All usage is tracked per user for analytics and budget enforcement

---

## Quick Start

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

Edit `backend/.env`:

```env
PROXY_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/proxy
PROXY_KEY_HASHER_SECRET=local-dev-secret-change-in-prod
PROXY_JWT_SECRET=local-jwt-secret-change-in-prod
PROXY_ADMIN_USERNAME=admin
PROXY_ADMIN_PASSWORD_HASH=<your-bcrypt-hash>
PROXY_BEDROCK_REGION=ap-northeast-2
```

Generate admin password hash:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt()).decode())"
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

## For End Users (SSO)

### Setup

1. Ensure your AWS SSO profile is configured
2. Configure `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://<API_GATEWAY_URL>",
    "AWS_PROFILE": "<your-sso-profile>",
    "AWS_REGION": "ap-northeast-2",
    "PROXY_TOKEN_SERVICE_URL": "https://<API_GATEWAY_URL>/auth/sso"
  },
  "apiKeyHelper": "/path/to/scripts/get-proxy-token.sh",
  "awsAuthRefresh": "aws sso login --profile <your-sso-profile>"
}
```

3. Login and start:

```bash
aws sso login --profile <your-sso-profile>
claude
```

The `apiKeyHelper` script automatically:
- Exports SSO credentials
- Calls `/auth/sso` with SigV4 signing
- Receives and caches an access key
- Returns the key to Claude Code

### Token Limits (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | 4096 | Max tokens for model responses |
| `MAX_THINKING_TOKENS` | 1024 | Budget for Extended Thinking |

---

## For Administrators

### Admin Dashboard

<p align="center">
  <img src="./assets/user-detail.gif" alt="user-detail" width="600">
</p>

| Feature | Description |
|---------|-------------|
| **User Management** | SSO users auto-provisioned on first login |
| **Group Management** | Organize users by SSO Permission Set |
| **Budget Control** | Set monthly USD limits per user or group |
| **Usage Analytics** | Token throughput, cost breakdown, top users |
| **Model Slots** | Configure which Bedrock models are available |

### Budget Management

- Set monthly USD limit per user or group
- Budget exceeded → 429 response
- Resets on 1st of each month (KST, UTC+9)

### Model Configuration

Configure model mappings via the admin dashboard (Model Slots) or environment variable:

```bash
PROXY_BEDROCK_DEFAULT_MODEL=global.anthropic.claude-sonnet-4-6
```

> See [Amazon Bedrock Supported Models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html) for model IDs.

### Cache Control (Bedrock)

Prompt caching is supported. Cache strategy is configurable per user:

| Strategy | Description |
|----------|-------------|
| `none` | No caching |
| `5m` (default) | 5-minute TTL |
| `1h` | 1-hour TTL (supported models only) |

---

## Deployment (AWS CDK)

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| AWS CLI 2.0+ | Configured with appropriate credentials |
| AWS CDK 2.0+ | `npm install -g aws-cdk` |

Required AWS permissions: VPC, ECS, RDS, Secrets Manager, KMS, API Gateway, Amplify.

### Deploy Infrastructure

```bash
cd infra
pip install -r requirements.txt
cdk bootstrap  # First time only
cdk deploy --all
```

This deploys:

| Stack | Resources |
|-------|-----------|
| **NetworkStack** | VPC, subnets, security groups |
| **DatabaseStack** | Aurora PostgreSQL Serverless v2 |
| **SecretsStack** | Secrets Manager (admin creds, JWT, hasher) |
| **ComputeStack** | ECS Fargate (with Bedrock IAM permissions) |
| **ApiGatewayStack** | HTTP API with IAM auth for `/auth/sso` |

### Deploy Frontend

```bash
cd frontend
VITE_BACKEND_API_URL=https://<API_GATEWAY_URL> ./scripts/amplify-bootstrap-deploy.sh
```

### IAM: SSO Users Need `execute-api:Invoke`

Attach the `SsoInvokePolicy` (output from ApiGatewayStack) to your SSO Permission Set roles so users can call `/auth/sso`.

---

## Project Structure

```
├── backend/          # FastAPI + SQLAlchemy + boto3
├── frontend/         # React + Vite + Tailwind
├── infra/            # AWS CDK stacks
└── scripts/          # get-proxy-token.sh (apiKeyHelper)
```

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
| `PROXY_BEDROCK_REGION` | ap-northeast-2 | AWS region for Bedrock |
| `PROXY_BEDROCK_DEFAULT_MODEL` | global.anthropic.claude-sonnet-4-6 | Default Bedrock model ID |
| `PROXY_CIRCUIT_FAILURE_THRESHOLD` | 3 | Failures before circuit opens |
| `PROXY_CIRCUIT_RESET_TIMEOUT` | 1800 | Circuit reset timeout (seconds) |
| `PROXY_LOCAL_ENCRYPTION_KEY` | - | 32-byte key for local dev |
| `PROXY_LOG_LEVEL` | INFO | Log level |
| `PROXY_CLOUDWATCH_METRICS_ENABLED` | true | Emit CloudWatch metrics |
| `PROXY_CLOUDWATCH_NAMESPACE` | ClaudeCodeProxy | CloudWatch namespace |

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, boto3, PostgreSQL |
| Frontend | React 18, Vite, Tailwind CSS |
| Infrastructure | AWS CDK, ECS Fargate, Aurora PostgreSQL, API Gateway, Amplify |
| Auth | AWS SSO + SigV4, HMAC-SHA256 access keys |
