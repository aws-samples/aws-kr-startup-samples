#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  DeepSeekV2LiteChatRealtimeEndpointStack
)

APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

sm_deepseek_v2_lite_chat_endpoint = DeepSeekV2LiteChatRealtimeEndpointStack(app, 'DeepSeekV2LiteChatEndpointStack',
  env=APP_ENV
)

app.synth()
