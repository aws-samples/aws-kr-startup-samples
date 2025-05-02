Read this in other languages: English, [Korean(한국어)](./README.kr.md)

# MCP Server CDK Project

This project includes a CDK stack that deploys a Python application to ECS EC2 and connects it to an ALB.

## Project Structure

```
mcp-server-cdk/
├── app/                    # Python application code
│   ├── app.py              # FastAPI application
│   ├── requirements.txt    # Application dependencies
│   └── Dockerfile          # Container image build file
├── stacks/                 # CDK stack code
│   └── mcp_server_amazon_ecs_stack.py  # ECS, ALB infrastructure definition
├── app.py                  # CDK app entry point
├── cdk.json               # CDK configuration file
├── requirements.txt       # CDK dependencies
└── source.bat            # Windows environment setup script
```

## Deployment Method

1. Activate the virtual environment:
```
$ source .venv/bin/activate  # Linux/Mac
$ source.bat                # Windows
```

2. Install the required dependencies:
```
$ pip install -r requirements.txt
```

3. Deploy with CDK:
```
$ cdk deploy
```

## Infrastructure Components

- VPC: 2 availability zones and 1 NAT gateway
- ECS Cluster: Cluster for running EC2-based services
- EC2 Instance: Using ARM-based c6g.xlarge instances
- ECS Service: Service consisting of 1 task
- Application Load Balancer: Routes internet traffic to the service
- Security Group: Allows HTTP(80) traffic

## Application

A FastAPI application that provides the following endpoints:
- `/`: Returns a basic greeting message
- `/health`: Health check endpoint (checked every 5 seconds)

## Notes

- The container runs on port 8000
- The ALB receives HTTP traffic on port 80
