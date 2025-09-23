#!/usr/bin/env python3
import os
import aws_cdk as cdk
from strands_agent_with_eventbridge_fargate.strands_agent_with_eventbridge_fargate_stack import StrandsAgentWithEventbridgeFargateStack

app = cdk.App()
StrandsAgentWithEventbridgeFargateStack(
    app, 
    "StrandsAgentWithEventbridgeFargateStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

app.synth()
