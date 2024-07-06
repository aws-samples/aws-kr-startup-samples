#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from rag_with_docdb import (
  VpcStack,
  LLMEndpointStack,
  SageMakerStudioStack,
  DocumentDBStack
)


APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

vpc_stack = VpcStack(app, 'RAGDocDBVPCStack',
  env=APP_ENV
)

docdb_stack = DocumentDBStack(app, 'RAGDocDBStack',
  vpc_stack.vpc,
  env=APP_ENV
)
docdb_stack.add_dependency(vpc_stack)

sm_studio_stack = SageMakerStudioStack(app, 'RAGSageMakerStudioInVPCStack',
  vpc_stack.vpc,
  docdb_stack.sg_docdb_client,
  env=APP_ENV
)
sm_studio_stack.add_dependency(docdb_stack)

sm_llm_endpoint = LLMEndpointStack(app, 'RAGDocDBLLMEndpointStack',
  env=APP_ENV
)
sm_llm_endpoint.add_dependency(sm_studio_stack)

app.synth()
