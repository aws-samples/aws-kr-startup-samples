#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from rag_with_kb import (
  BedrockKnowledgeBaseStack,
  SageMakerStudioStack,
  VpcStack
)


AWS_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

kb_for_bedrock_stack = BedrockKnowledgeBaseStack(app, 'BedrockKnowledgeBaseStack',
  env=AWS_ENV)

vpc_stack = VpcStack(app, 'BedrockKBVpcStack',
  env=AWS_ENV)
vpc_stack.add_dependency(kb_for_bedrock_stack)

sm_studio_stack = SageMakerStudioStack(app, 'BedrockKBSageMakerStudioStack',
  vpc_stack.vpc,
  env=AWS_ENV)
sm_studio_stack.add_dependency(vpc_stack)

app.synth()
