# CDK Deployment for Observability Assistant

This directory contains CDK and Helm deployment scripts for the Observability Assistant project. It deploys three components to an existing EKS cluster:

- **Observability Assistant**: Main chatbot application
- **Tempo MCP Server**: Handles Grafana Tempo integration
- **Grafana MCP Server**: Handles Grafana API integration

## Prerequisites

- **AWS CDK**: Install with `npm install -g aws-cdk`
- **Helm**: Install with `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash`
- **Python 3.11+**: For CDK dependencies
- **Existing EKS cluster**: The deployment targets an existing cluster
- **Grafana instance**: With API access and API key
- **Tempo instance**: For distributed tracing

## Setup

1. **Create and activate virtual environment**:
   ```bash
   cd cdk
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   # Set required environment variables for MCP servers
   export GRAFANA_URL="https://your-grafana-instance.com"
   export GRAFANA_API_KEY="your-grafana-api-key"
   export TEMPO_URL="https://your-tempo-instance.com"
   export BEDROCK_MODEL_ID="anthropic.claude-3-7-sonnet-20250219-v1:0"
   export BEDROCK_REGION="us-east-1"
   ```

## Deployment

**Deploy everything with one command**:
```bash
./deploy.sh <cluster-name> [region]
```

Example:
```bash
./deploy.sh my-eks-cluster ap-northeast-2
```

This script will:
1. Build and push Docker images to ECR
2. Create IAM roles with Bedrock permissions
3. Set up Pod Identity associations
4. Deploy Helm chart with all three services

## Access

Once deployed, access the web interface via the external IP of the `observability-assistant` service:

```bash
kubectl get service observability-assistant -n observability
```

## Cleanup

**Remove everything**:
```bash
./cleanup.sh <cluster-name> [region]
```

This will uninstall the Helm chart and destroy all CDK resources.