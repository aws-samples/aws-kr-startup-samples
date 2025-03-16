#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  DeepSeekR1SGLangRealtimeEndpointStack
)

APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

sm_realtime_endpoint = DeepSeekR1SGLangRealtimeEndpointStack(
  app,
  'DeepSeekR1SGLangEndpointStack',
  env=APP_ENV
)

app.synth()
