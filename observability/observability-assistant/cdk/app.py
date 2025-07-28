#!/usr/bin/env python3
import aws_cdk as cdk
import os
from observability_assistant_stack import ObservabilityAssistantStack

app = cdk.App()

# Get context values with fallbacks
cluster_name = app.node.try_get_context("cluster_name") or os.environ.get("EKS_CLUSTER_NAME")
if not cluster_name:
    raise ValueError(
        "cluster_name context is required. Use one of:\n"
        "  cdk deploy -c cluster_name=your-cluster-name\n"
        "  export EKS_CLUSTER_NAME=your-cluster-name"
    )

# Get region and account with fallbacks
region = (
    app.node.try_get_context("region") or 
    os.environ.get("AWS_DEFAULT_REGION") or 
    os.environ.get("AWS_REGION") or 
    "ap-northeast-2"
)

account = (
    app.node.try_get_context("account") or 
    os.environ.get("CDK_DEFAULT_ACCOUNT")
)

# Only print deployment info if we're not just bootstrapping
if not os.environ.get("CDK_BOOTSTRAP_ONLY"):
    print(f"Deploying to cluster: {cluster_name}")
    print(f"Region: {region}")
    print(f"Account: {account or 'auto-detected'}")

ObservabilityAssistantStack(
    app, 
    "ObservabilityAssistantStack",
    cluster_name=cluster_name,
    env=cdk.Environment(
        account=account,
        region=region
    )
)

app.synth()