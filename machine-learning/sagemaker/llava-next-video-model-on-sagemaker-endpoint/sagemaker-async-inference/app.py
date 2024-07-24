#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  LlaVaNeXTVideoAsyncEndpointStack,
  SageMakerAsyncEndpointAutoScalingStack
)

APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

sm_llava_video_endpoint = LlaVaNeXTVideoAsyncEndpointStack(app,
  'LlaVaNeXTVideoAsyncEndpointStack',
  env=APP_ENV
)

sm_async_endpoint_autoscale = SageMakerAsyncEndpointAutoScalingStack(app,
  'LlaVaNeXTVideoAsyncEndpointAutoScalingStack',
  sm_llava_video_endpoint.sagemaker_endpoint,
  env=APP_ENV
)
sm_async_endpoint_autoscale.add_dependency(sm_llava_video_endpoint)

app.synth()
