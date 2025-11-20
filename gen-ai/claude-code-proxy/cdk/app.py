#!/usr/bin/env python3
import aws_cdk as cdk
from claude_proxy_fargate_stack import ClaudeProxyFargateStack

app = cdk.App()

ClaudeProxyFargateStack(
    app,
    "ClaudeProxyFargateStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)

app.synth()
