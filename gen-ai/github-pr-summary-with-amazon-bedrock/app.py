#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_stacks import GitHubPRSummaryStack

AWS_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

stack_name = 'GitHubPRSummaryWithBedrockStack' if 'LOCAL_TESTING' not in os.environ else 'PythonStack'

app = cdk.App()
GitHubPRSummaryStack(app,
    stack_name,
    env=AWS_ENV
)

app.synth()
