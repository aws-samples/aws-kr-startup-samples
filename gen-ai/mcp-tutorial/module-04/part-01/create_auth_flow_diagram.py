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

# Create the authentication flow diagram
with Diagram("MCP Authentication Flow - Detailed", show=False, direction="TB", filename="mcp-auth-flow"):
    
    # User
    user = User("Developer\n(Browser)")
    
    # AWS Infrastructure
    with Cluster("AWS Cloud"):
        # Single EC2 Instance hosting both apps
        with Cluster("EC2 Instance (c5.large)"):
            with Cluster("Port 8501"):
                client = Lambda("MCP Client\n(Streamlit)")
            with Cluster("Port 8080"):
                server = Lambda("MCP Server\n(FastAPI + SSE)")
        
        # AWS Services
        cognito = Cognito("Amazon Cognito\nUser Pool")
        bedrock = Bedrock("Amazon Bedrock\n(Nova Lite)")
    
    # Authentication Flow (numbered steps)
    user >> Edge(label="1. Login Form", style="dashed", color="blue") >> client
    client >> Edge(label="2. Username/Password", style="dashed", color="blue") >> cognito
    cognito >> Edge(label="3. JWT Access Token", style="dashed", color="green") >> client
    
    # MCP Communication with Auth
    client >> Edge(label="4. SSE Request\n+ Bearer Token", style="bold", color="red") >> server
    server >> Edge(label="5. Verify Token", style="dashed", color="orange") >> cognito
    cognito >> Edge(label="6. User Info", style="dashed", color="green") >> server
    server >> Edge(label="7. MCP Protocol\n(Authenticated)", style="bold", color="green") >> client
    
    # AI Integration
    client >> Edge(label="8. AI Query", style="dotted", color="purple") >> bedrock

print("Authentication flow diagram created successfully!")
