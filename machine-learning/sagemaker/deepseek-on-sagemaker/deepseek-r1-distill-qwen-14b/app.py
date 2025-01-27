#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  DeepSeekR1RealtimeEndpointStack
)

APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

sm_realtime_endpoint = DeepSeekR1RealtimeEndpointStack(
  app, 'DeepSeekR1EndpointStack',
  env=APP_ENV
)

app.synth()
