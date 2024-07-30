#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from rag_with_memorydb import (
  VpcStack,
  SageMakerStudioStack,
  MemoryDBAclStack,
  MemoryDBStack
)


APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

vpc_stack = VpcStack(app, 'RAGMemoryDBVPCStack',
  env=APP_ENV)

memorydb_acl_stack = MemoryDBAclStack(app, 'RAGMemoryDBAclStack',
  env=APP_ENV)

memorydb_stack = MemoryDBStack(app, 'RAGMemoryDBStack',
  vpc_stack.vpc,
  memorydb_acl_stack.memorydb_acl,
  env=APP_ENV)
memorydb_stack.add_dependency(memorydb_acl_stack)

sm_studio_stack = SageMakerStudioStack(app, 'RAGSageMakerStudioInVPCStack',
  vpc_stack.vpc,
  memorydb_stack.sg_memorydb_client,
  env=APP_ENV
)
sm_studio_stack.add_dependency(memorydb_stack)

app.synth()
