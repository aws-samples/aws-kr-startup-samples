#!/usr/bin/env python3
import os
import aws_cdk as cdk
from waf_log_generator.waf_log_generator_stack import WafLogGeneratorStack

app = cdk.App()
WafLogGeneratorStack(app, "WafLogGeneratorStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION')
    )
)

app.synth()
