#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  VideoLlaVaRealtimeEndpointStack,
  SageMakerRealtimeEndpointAutoScalingStack
)

APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

sm_video_llava_endpoint = VideoLlaVaRealtimeEndpointStack(app, 'VideoLlaVaRealtimeEndpointStack',
  env=APP_ENV
)

sm_realtime_endpoint_autoscale = SageMakerRealtimeEndpointAutoScalingStack(app, 'VideoLlaVaRealtimeEndpointAutoScalingStack',
  sm_video_llava_endpoint.sagemaker_endpoint,
  env=APP_ENV
)
sm_realtime_endpoint_autoscale.add_dependency(sm_video_llava_endpoint)

app.synth()
