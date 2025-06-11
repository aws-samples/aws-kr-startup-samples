#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_stacks.qwen3_embedding_0_6b_endpoint_stack import (
    Qwen3Embedding06bEndpointStack,
)


app = cdk.App()

Qwen3Embedding06bEndpointStack(
    app,
    "Qwen3Embedding06bEndpointStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

app.synth()
