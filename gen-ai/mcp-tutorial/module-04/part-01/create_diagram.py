#!/usr/bin/env python3

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, Lambda
from diagrams.aws.security import Cognito, IAM
from diagrams.aws.ml import Bedrock
from diagrams.aws.management import SystemsManager
from diagrams.aws.devtools import CloudDevelopmentKit
from diagrams.aws.network import VPC
from diagrams.generic.blank import Blank
from diagrams.onprem.client import User

# Create the diagram
with Diagram("CLEANAUTH - MCP Authentication System", show=False, direction="TB", filename="mcp-auth-architecture"):
    
    # User
    user = User("Developer")
    
    # AWS Infrastructure
    with Cluster("AWS Cloud"):
        # VPC and EC2
        with Cluster("VPC - Public Subnet"):
            ec2 = EC2("EC2 Instance\n(c5.large)")
        
        # AWS Services
        with Cluster("AWS Services"):
            cognito = Cognito("Amazon Cognito\nUser Pool")
            bedrock = Bedrock("Amazon Bedrock\n(Nova Lite)")
            ssm = SystemsManager("Systems Manager\nSession Manager")
            iam = IAM("IAM Role")
    
    # Applications running on EC2
    with Cluster("MCP Applications (on EC2)"):
        server = Lambda("MCP Server\nFastAPI (Port 8080)")
        client = Lambda("MCP Client\nStreamlit (Port 8501)")
    
    # Infrastructure as Code
    cdk = CloudDevelopmentKit("AWS CDK\nInfrastructure")
    
    # User interactions
    user >> Edge(label="Web Access") >> client
    user >> Edge(label="SSH/Session") >> ssm
    
    # Authentication flow
    client >> Edge(label="Login") >> cognito
    server >> Edge(label="Verify Token") >> cognito
    
    # MCP Communication
    client >> Edge(label="SSE/MCP Protocol") >> server
    
    # AI Integration
    client >> Edge(label="AI Queries") >> bedrock
    
    # Infrastructure relationships
    cdk >> Edge(label="Deploy") >> ec2
    ec2 >> Edge(label="Host") >> [server, client]
    ec2 >> Edge(label="Assume Role") >> iam
    iam >> Edge(label="Access") >> bedrock
    ssm >> Edge(label="Connect") >> ec2

print("Diagram created successfully!")
