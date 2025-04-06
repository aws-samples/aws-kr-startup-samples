#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  QwenVLSGLangRealtimeEndpointStack,
  ECRStack
)

APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

ecr_stack = ECRStack(app, 'SGLangECRStack',
  env=APP_ENV
)

sm_realtime_endpoint = QwenVLSGLangRealtimeEndpointStack(app,
  'QwenVLSGLangRealtimeEndpointStack',
  env=APP_ENV
)
sm_realtime_endpoint.add_dependency(ecr_stack)

app.synth()