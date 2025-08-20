#!/usr/bin/env python3
import aws_cdk as cdk
from agent_lambda_stack import AgentLambdaStack


app = cdk.App()
AgentLambdaStack(app, "AgentLambdaStack")

app.synth()