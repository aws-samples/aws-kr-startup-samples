# Claude Code Proxy - Fargate Deployment

## Prerequisites

- AWS CLI configured
- Python 3.12+
- Docker
- AWS CDK CLI: `npm install -g aws-cdk`

## Setup

```bash
cd cdk
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Deploy

```bash
# Public ECR 403 에러 방지 (권장)
docker logout public.ecr.aws

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy
cdk deploy
```

The stack will create:
- VPC with public/private subnets
- Application Load Balancer (ALB)
- ECS Fargate Service (1 task, 0.5 vCPU, 1GB RAM)
- DynamoDB table for rate limiting
- CloudWatch Logs

## Access

After deployment, CDK will output:
- `LoadBalancerDNS`: ALB DNS name
- `ServiceURL`: Full service URL

Test:
```bash
curl -X POST "http://<ALB-DNS>/v1/messages" \
  -H "x-api-key: YOUR_ANTHROPIC_API_KEY" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":100,"messages":[{"role":"user","content":"Hi"}]}'
```

## Cleanup

```bash
cdk destroy
```

## Logs

View logs in CloudWatch:
```bash
aws logs tail /aws/ecs/claude-proxy --follow
```

