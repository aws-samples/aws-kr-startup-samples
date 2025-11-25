# Strands MCP Code Execution Demo

This repository demonstrates Strands agent implementations instrumented with Langfuse tracing and AWS MCP servers, following the workflow outlined in [Anthropic – *Code execution with MCP*](https://www.anthropic.com/engineering/code-execution-with-mcp).

![Langfuse trace comparison](result.png)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp env.example .env
# Edit .env to set Langfuse keys and host

# Use the unified run script
python run.py direct "What is AWS Lambda?"
python run.py code-exec "Check EKS cluster status" --user-id demo
```

### Optional: Local Langfuse Stack

```bash
# Start Langfuse with Docker Compose
docker compose up -d

# View logs
docker compose logs -f langfuse-web

# Stop
docker compose down
```

The Langfuse web UI will be accessible at http://localhost:3000.

## Project Structure

```
code-execution-with-mcp-strands-sdk/
├── agents/                      # Agent implementations
│   ├── agent_mcp_direct.py     # Direct MCP server connection approach
│   └── agent_code_execution.py # Dynamic tool discovery with code execution
├── core/                        # Shared utilities
│   ├── langfuse_tracing.py     # Langfuse tracing logic
│   ├── mcp_config.py           # MCP server configuration and clients
│   └── logging.py              # Logging configuration
├── mcp-servers/                 # Python wrappers for MCP tools
│   ├── amazon_ecs/             # ECS-related tools
│   ├── amazon_eks/             # EKS-related tools
│   ├── aws_cdk/                # CDK-related tools
│   └── aws_documentation/      # AWS documentation search
├── docker-compose.yml           # Local Langfuse deployment
├── run.py                       # Unified execution script
├── requirements.txt
└── env.example
```

## Agent Types

### 1. MCP Direct Agent (`agent_mcp_direct.py`)

**Features:**
- Initializes all AWS MCP servers (documentation, EKS, ECS, CDK) at startup
- Traditional approach with tools passed directly to the Agent
- Fast response time with simple architecture

**Usage:**
```bash
python run.py direct "Explain AWS Lambda"
python run.py direct "How do I create an ECS task definition?" --user-id demo
```

Or run directly:
```bash
python -m agents.agent_mcp_direct "What is AWS Lambda?"
```

### 2. Code Execution Agent (`agent_code_execution.py`)

**Features:**
- Applies Anthropic's code execution playbook
- `search_tools` → `file_read` → `python_repl` workflow
- Dynamically discovers and executes MCP tools as needed
- Answers natural language questions directly, leverages MCP for infrastructure tasks

**Usage:**
```bash
python run.py code-exec "Get the list of pods in my EKS cluster"
python run.py code-exec "How to deploy a new service on ECS" --user-id demo
```

Or run directly:
```bash
python -m agents.agent_code_execution "Find EKS troubleshooting guide"
```

## Run Script (`run.py`)

The unified run script allows you to execute all agents through a single interface.

**Usage:**
```bash
python run.py <agent_type> <prompt> [--user-id USER_ID]
```

**Options:**
- `agent_type`: `direct` or `code-exec`
- `prompt`: Question or command to pass to the agent
- `--user-id`: User ID to record in Langfuse traces (default: local-user)
- `--list`: List available agent types

**Examples:**
```bash
# List available agents
python run.py --list

# Run MCP Direct Agent
python run.py direct "What is Amazon ECS?"

# Run Code Execution Agent
python run.py code-exec "List all EKS clusters" --user-id alice
```

## Langfuse Tracing

Configure the following environment variables in your `.env` file:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_USER_ID=local-user
```

Both agents automatically initialize Langfuse. If credentials are missing, they log a warning and continue execution without tracing.

### Local Langfuse Deployment

`docker-compose.yml` provides a complete Langfuse stack including:
- PostgreSQL (database)
- Redis (caching)
- ClickHouse (analytics)
- MinIO (S3-compatible storage)
- Langfuse Web & Worker

## MCP Servers

This project uses the following AWS MCP servers:

| Server | Package | Description |
|--------|---------|-------------|
| AWS Documentation | `awslabs.aws-documentation-mcp-server` | Search AWS documentation |
| Amazon EKS | `awslabs.eks-mcp-server` | EKS cluster management and troubleshooting |
| Amazon ECS | `awslabs-ecs-mcp-server` | ECS task definitions and deployment |
| AWS CDK | `awslabs.cdk-mcp-server` | CDK guidance and best practices |

All servers are configured in `core/mcp_config.py` and run via `uvx`.

## Development

### Adding a New MCP Tool Wrapper

1. Create a Python file in the appropriate directory under `mcp-servers/`
2. Import `call_mcp_tool` from `core.mcp_config`
3. Implement your tool function:

```python
from core.mcp_config import call_mcp_tool

SERVER_KEY = "amazon-eks"

def my_new_tool(param1: str, param2: int):
    """Tool description"""
    return call_mcp_tool(SERVER_KEY, "tool_name", {
        "param1": param1,
        "param2": param2,
    })
```

### Adding a New MCP Server

1. Add server configuration to `MCP_REGISTRY` in `core/mcp_config.py`
2. Create a new directory under `mcp-servers/`
3. Write Python wrapper functions

## Troubleshooting

**Import Errors**
→ Ensure your virtual environment has installed `requirements.txt`

**Langfuse Issues**
→ Check logs with `docker compose logs -f langfuse-web`
→ Verify credentials and ports

**MCP Failures**
→ Verify AWS CLI credentials
→ Check environment variable overrides (e.g., `AWS_DOCS_MCP_LOG_LEVEL`, `ECS_MCP_ALLOW_WRITE`)

**Adjusting Log Level**
→ Set `LOG_LEVEL=DEBUG` in your `.env` file

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | - |
| `LANGFUSE_HOST` | Langfuse host URL | `http://localhost:3000` |
| `LANGFUSE_USER_ID` | Default user ID | `local-user` |
| `AWS_DOCS_MCP_LOG_LEVEL` | AWS Docs MCP log level | `ERROR` |
| `EKS_MCP_LOG_LEVEL` | EKS MCP log level | `ERROR` |
| `ECS_MCP_LOG_LEVEL` | ECS MCP log level | `ERROR` |
| `ECS_MCP_ALLOW_WRITE` | Allow ECS write operations | `false` |
| `ECS_MCP_ALLOW_SENSITIVE_DATA` | Allow ECS sensitive data access | `false` |
| `CDK_MCP_LOG_LEVEL` | CDK MCP log level | `ERROR` |

## License

This project is for demonstration purposes. Implement appropriate security and error handling before production use.
