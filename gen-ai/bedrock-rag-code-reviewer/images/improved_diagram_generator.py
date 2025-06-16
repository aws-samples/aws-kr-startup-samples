#!/usr/bin/env python3
"""
AWS Architecture Diagram Generator for Bedrock RAG Code Reviewer
Creates a visual representation of the system architecture with improved formatting
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.network import APIGateway
from diagrams.aws.storage import S3
from diagrams.aws.ml import Bedrock
from diagrams.aws.analytics import AmazonOpensearchService
from diagrams.onprem.vcs import Github
from diagrams.saas.chat import Slack

def create_architecture_diagram():
    """Create the Bedrock RAG Code Reviewer architecture diagram with improved formatting"""
    
    # Configure diagram settings for better alignment
    graph_attr = {
        "fontsize": "45",
        "bgcolor": "white",
        "pad": "1.5",
        "splines": "spline",
        "nodesep": "2.0",
        "ranksep": "2.0",
        "concentrate": "true"
    }
    
    node_attr = {
        "fontsize": "14",
        "fontname": "Arial",
        "fontcolor": "black"
    }
    
    edge_attr = {
        "fontsize": "14",
        "fontname": "Arial Bold",
        "fontcolor": "black",
        "penwidth": "2.0",
        "labeldistance": "3.0",
        "labelangle": "0"
    }
    
    with Diagram(
        "Bedrock RAG Code Reviewer Architecture", 
        show=False, 
        direction="TB", 
        filename="bedrock_rag_architecture_v2",
        graph_attr=graph_attr,
        node_attr=node_attr,
        edge_attr=edge_attr,
        outformat="png"
    ):
        
        # External services
        github = Github("GitHub Repository")
        slack = Slack("Slack")
        
        # AWS Services
        with Cluster("AWS Cloud", graph_attr={"bgcolor": "#E8F4FD", "style": "rounded", "fontsize": "16"}):
            
            # API Gateway
            api_gateway = APIGateway("API Gateway")
            
            # Lambda Functions
            with Cluster("Lambda Functions", graph_attr={"bgcolor": "#FFF2CC", "fontsize": "14"}):
                webhook_processor = Lambda("github-webhook-processor")
                git_analyzer = Lambda("git-push-analyzer")
            
            # Bedrock Services
            with Cluster("Amazon Bedrock", graph_attr={"bgcolor": "#FFE6E6", "fontsize": "14"}):
                knowledge_base = Bedrock("Knowledge Base")
                claude_model = Bedrock("Claude 3.5 Sonnet")
                embedding_model = Bedrock("Titan Embed Text v2")
            
            # Storage and Search
            s3_bucket = S3("S3 Bucket")
            opensearch = AmazonOpensearchService("OpenSearch Serverless")
        
        # Define the main workflow connections with improved spacing
        github >> Edge(label="  1. Webhook POST  ", color="darkblue", style="bold", fontsize="14", penwidth="2.5", labeldistance="10", headport="w", tailport="n") >> api_gateway
        api_gateway >> Edge(label="  2. Trigger  ", color="darkblue", style="bold", fontsize="14", penwidth="2.5", labeldistance="10") >> webhook_processor
        webhook_processor >> Edge(label="  3. Invoke  ", color="darkblue", style="bold", fontsize="14", penwidth="2.5", labeldistance="10") >> git_analyzer
        git_analyzer >> Edge(label="  4. Fetch files  ", color="darkgreen", fontsize="14", penwidth="2.5", labeldistance="10") >> github
        git_analyzer >> Edge(label="  5. Query context  ", color="purple", fontsize="14", penwidth="2.5", labeldistance="10") >> knowledge_base
        knowledge_base >> Edge(label="  6. Retrieve similar code  ", color="purple", fontsize="14", penwidth="2.5", labeldistance="10") >> opensearch
        knowledge_base >> Edge(label="  7. Generate embeddings  ", color="darkorange", fontsize="14", penwidth="2.5", labeldistance="10") >> embedding_model
        git_analyzer >> Edge(label="  8. Generate review  ", color="darkred", fontsize="14", penwidth="2.5", labeldistance="10") >> claude_model
        git_analyzer >> Edge(label="  9. Store report  ", color="brown", fontsize="14", penwidth="2.5", labeldistance="10") >> s3_bucket
        git_analyzer >> Edge(label="  10. Send notification  ", color="darkgreen", fontsize="14", penwidth="2.5", labeldistance="10") >> slack
        
        # Data flow for indexing (dotted lines)
        git_analyzer >> Edge(label="  Index code chunks  ", style="dashed", color="black", fontsize="12", penwidth="2.0", labeldistance="10") >> opensearch
        s3_bucket >> Edge(label="  Store embeddings  ", style="dashed", color="black", fontsize="12", penwidth="2.0", labeldistance="10") >> opensearch

if __name__ == "__main__":
    create_architecture_diagram()
    print("Improved architecture diagram created successfully!")
    print("Generated file: bedrock_rag_architecture_v2.png")
