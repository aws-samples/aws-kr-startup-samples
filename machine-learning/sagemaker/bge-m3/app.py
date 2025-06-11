#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_stacks.bge_m3_endpoint_stack import BgeM3EndpointStack


app = cdk.App()

BgeM3EndpointStack(
    app,
    "BgeM3EndpointStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

app.synth()
