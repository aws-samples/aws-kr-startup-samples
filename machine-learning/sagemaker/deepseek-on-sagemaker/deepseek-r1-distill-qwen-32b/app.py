#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  DeepSeekR1JumpStartEndpointStack,
  SageMakerRealtimeEndpointAutoScalingStack,
)

APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

sm_jumpstart_endpoint = DeepSeekR1JumpStartEndpointStack(app, 'DeepSeekR1JumpStartEndpointStack',
  env=APP_ENV
)

sm_endpoint_autoscale = SageMakerRealtimeEndpointAutoScalingStack(app, 'DeepSeekR1EndpointAutoScalingStack',
  sm_jumpstart_endpoint.sagemaker_endpoint,
  env=APP_ENV
)
sm_endpoint_autoscale.add_dependency(sm_jumpstart_endpoint)

app.synth()
