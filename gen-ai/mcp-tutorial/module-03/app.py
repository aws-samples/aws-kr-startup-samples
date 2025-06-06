#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stack.cdk_stack import McpServerAmazonECSStack


app = cdk.App()
McpServerAmazonECSStack(app, "MCPStreamlitAppStack", env=cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"])
)

app.synth()
