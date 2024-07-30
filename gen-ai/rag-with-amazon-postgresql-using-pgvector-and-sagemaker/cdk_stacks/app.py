#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from rag_with_pgvector import (
  VpcStack,
  AuroraPostgresqlStack,
  SageMakerStudioStack,
  EmbeddingEndpointStack,
  LLMEndpointStack
)

APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

vpc_stack = VpcStack(app, 'RAGVpcStack',
  env=APP_ENV)

aurora_pgsql_stack = AuroraPostgresqlStack(app, 'RAGPgVectorStack',
  vpc_stack.vpc,
  env=APP_ENV
)
aurora_pgsql_stack.add_dependency(vpc_stack)

sm_studio_stack = SageMakerStudioStack(app, 'RAGSageMakerStudioStack',
  vpc_stack.vpc,
  aurora_pgsql_stack.sg_rds_client,
  env=APP_ENV
)
sm_studio_stack.add_dependency(aurora_pgsql_stack)

sm_embedding_endpoint = EmbeddingEndpointStack(app, 'EmbeddingEndpointStack',
  env=APP_ENV
)
sm_embedding_endpoint.add_dependency(sm_studio_stack)

sm_llm_endpoint = LLMEndpointStack(app, 'LLMEndpointStack',
  env=APP_ENV
)
sm_llm_endpoint.add_dependency(sm_studio_stack)

app.synth()
