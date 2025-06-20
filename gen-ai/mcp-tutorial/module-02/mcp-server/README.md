Read this in other languages: English, [Korean(한국어)](./README.ko.md)

# MCP Server CDK Deployment

This project deploys a Model Context Protocol (MCP) weather server to AWS using AWS CDK. The infrastructure includes ECS on EC2 instances with an Application Load Balancer, providing a scalable and production-ready deployment for MCP servers with streamable HTTP transport.

## Architecture Overview

The CDK stack creates a complete AWS infrastructure for hosting an MCP server:

```
                    Internet
                       │
                       ▼
              ┌─────────────────┐
              │ Application     │
              │ Load Balancer   │
              │   (Port 80)     │
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   ECS Cluster   │
              │                 │
              │  ┌─────────────┐│
              │  │ ECS Service ││
              │  │             ││
              │  │ ┌─────────┐ ││
              │  │ │MCP Server│ ││
              │  │ │FastMCP  │ ││
              │  │ │Port 8000│ ││
              │  │ │         │ ││
              │  │ │Weather  │ ││
              │  │ │ Tools   │ ││
              │  │ └─────────┘ ││
              │  └─────────────┘│
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ National Weather│
              │  Service API    │
              │ (weather.gov)   │
              └─────────────────┘
```

## AWS Infrastructure Components

### Network Layer
- **VPC**: Custom VPC with 2 availability zones for high availability
- **Subnets**: Public subnets for ALB, private subnets for ECS tasks
- **NAT Gateway**: Single NAT gateway for outbound internet access from private subnets
- **Internet Gateway**: Attached to VPC for public internet access

### Compute Layer
- **ECS Cluster**: Managed container orchestration service
- **EC2 Instances**: ARM-based c6g.xlarge instances for cost-effective performance
- **Auto Scaling Group**: Maintains desired capacity of 1 instance
- **Task Definition**: Defines container specifications and resource allocation

### Load Balancing
- **Application Load Balancer (ALB)**: Distributes incoming traffic across ECS tasks
- **Target Group**: Routes traffic to healthy ECS tasks on port 8000
- **Health Checks**: Monitors `/health` endpoint every 5 seconds
- **Listener**: Accepts HTTP traffic on port 80

### Security
- **Security Groups**: Configured to allow HTTP traffic on port 80
- **IAM Roles**: Least privilege access for ECS tasks and services
- **VPC Isolation**: Private subnets protect container workloads

## Project Structure

```
mcp-server/
├── app/                                    # MCP Server Application
│   ├── main.py                            # FastMCP weather server implementation
│   ├── pyproject.toml                     # Python project configuration
│   ├── Dockerfile                         # Container image definition
│   ├── uv.lock                           # Dependency lock file
│   └── .gitignore                        # Git ignore patterns
├── stacks/                               # CDK Infrastructure Code
│   ├── __init__.py                       # Python package init
│   └── mcp_server_amazon_ecs_stack.py    # Main CDK stack definition
├── app.py                                # CDK application entry point
├── cdk.json                              # CDK configuration
├── requirements.txt                      # CDK dependencies
├── source.bat                            # Windows environment setup
└── README.md                             # This documentation
```

## MCP Server Application

The containerized application provides weather data through MCP tools:

### Available Tools
- **get_alerts**: Retrieves active weather alerts for US states
- **get_forecast**: Provides detailed weather forecasts for coordinates

### Configuration
- **Transport**: Streamable HTTP on port 8000
- **API Integration**: National Weather Service (NWS) API
- **Health Check**: `/health` endpoint for load balancer monitoring

## Prerequisites

- AWS CLI configured with appropriate credentials
- Node.js 18+ and npm
- Python 3.9+
- AWS CDK CLI installed (`npm install -g aws-cdk`)

## Installation and Deployment

### 1. Environment Setup

Clone the repository and navigate to the project directory:
```bash
cd module-02/mcp-server
```

### 2. Install Dependencies

Install CDK dependencies:
```bash
pip install -r requirements.txt
```

### 3. CDK Bootstrap (First Time Only)

Bootstrap your AWS environment for CDK:
```bash
cdk bootstrap aws://ACCOUNT-NUMBER/REGION
```

### 4. Deploy Infrastructure

Deploy the stack:
```bash
cdk deploy
```

### 5. Verify Deployment

After deployment, you'll receive outputs including:
- ALB DNS name for accessing the MCP server
- ECS service name
- ECS cluster name

## Configuration

### Instance Configuration
- **Instance Type**: c6g.xlarge (ARM-based)
- **Desired Capacity**: 1 instance
- **Memory Limit**: 4096 MiB per task
- **CPU**: 2048 CPU units per task

### Load Balancer Configuration
- **Protocol**: HTTP
- **Port**: 80 (external), 8000 (container)
- **Health Check Path**: `/health`
- **Health Check Interval**: 5 seconds

### Network Configuration
- **VPC CIDR**: Auto-assigned
- **Availability Zones**: 2
- **NAT Gateways**: 1 (cost-optimized)

## Monitoring and Logging

### CloudWatch Integration
- **Container Logs**: Automatically shipped to CloudWatch Logs
- **Log Group**: `/aws/ecs/McpServerAmazonECSStack`
- **Metrics**: ECS service and ALB metrics available in CloudWatch

### Health Monitoring
- **ALB Health Checks**: Continuous monitoring of container health
- **Auto Recovery**: Unhealthy tasks are automatically replaced
- **CloudWatch Alarms**: Can be configured for automated alerting

## Scaling Configuration

### Current Setup
- **Desired Capacity**: 1 task
- **Instance Count**: 1 EC2 instance

### Scaling Options
To increase capacity, modify the stack:
```python
# In mcp_server_amazon_ecs_stack.py
desired_count=2,  # Increase task count
desired_capacity=2,  # Increase EC2 instance count
```

## Cost Optimization

### Current Configuration
- **Instance Type**: c6g.xlarge (ARM-based for cost efficiency)
- **NAT Gateway**: Single NAT gateway shared across AZs
- **Load Balancer**: Single ALB for the application

### Estimated Monthly Costs
- EC2 Instance (c6g.xlarge): ~$140/month
- Application Load Balancer: ~$20/month
- NAT Gateway: ~$45/month
- Data Transfer: Variable based on usage

## Connecting MCP Clients

Once deployed, connect MCP clients using the ALB DNS name:

```json
{
  "mcpServers": {
    "weather": {
      "command": "http",
      "args": ["http://YOUR-ALB-DNS-NAME"]
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Deployment Failures**
   - Verify AWS credentials and permissions
   - Check CDK bootstrap status
   - Ensure Docker is running for container builds

2. **Health Check Failures**
   - Verify container starts successfully
   - Check CloudWatch logs for application errors
   - Confirm health endpoint returns 200 status

3. **Connection Issues**
   - Verify security group rules allow port 80
   - Check ALB target group health
   - Ensure tasks are running in private subnets

### Useful Commands

```bash
# Check stack status
cdk diff

# View CloudFormation events
aws cloudformation describe-stack-events --stack-name McpServerAmazonECSStack

# Check ECS service status
aws ecs describe-services --cluster CLUSTER-NAME --services SERVICE-NAME

# View container logs
aws logs tail /aws/ecs/McpServerAmazonECSStack --follow
```

## Cleanup

To avoid ongoing costs, destroy the stack when no longer needed:

```bash
cdk destroy
```

This will remove all AWS resources created by the stack.

## Security Considerations

- **Network Isolation**: ECS tasks run in private subnets
- **Least Privilege**: IAM roles follow principle of least privilege
- **HTTPS**: Consider adding SSL/TLS termination at the ALB level
- **VPC Endpoints**: Consider adding VPC endpoints for AWS services to reduce NAT costs

## Further Customization

The stack can be extended with additional features:
- **Auto Scaling**: Configure ECS service auto scaling based on metrics
- **HTTPS**: Add SSL certificates and HTTPS listeners
- **Custom Domain**: Route 53 integration for custom domain names
- **Monitoring**: Enhanced CloudWatch dashboards and alarms
- **Secrets Management**: AWS Secrets Manager integration for sensitive data