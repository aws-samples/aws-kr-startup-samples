#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.mcp_proxy_stack import McpProxyStack


app = cdk.App()
McpProxyStack(app, "McpProxyStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
        region="ap-northeast-2"
    ),

)

app.synth()
