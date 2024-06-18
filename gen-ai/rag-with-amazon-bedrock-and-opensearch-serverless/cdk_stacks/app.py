#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

from rag_with_bedrock_aoss import (
  VpcStack,
  OpsServerlessVectorSearchStack,
  SageMakerStudioStack
)

import aws_cdk as cdk


APP_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION'))

app = cdk.App()

vpc_stack = VpcStack(app, 'RAGAppVpcStack',
  env=APP_ENV
)

sm_studio_stack = SageMakerStudioStack(app, 'RAGAppSageMakerStudioStack',
  vpc_stack.vpc,
  env=APP_ENV
)
sm_studio_stack.add_dependency(vpc_stack)

ops_stack = OpsServerlessVectorSearchStack(app, 'RAGOpenSearchServerlessStack',
  sm_studio_stack.sagemaker_execution_role_arn,
  env=APP_ENV
)
ops_stack.add_dependency(sm_studio_stack)

app.synth()
