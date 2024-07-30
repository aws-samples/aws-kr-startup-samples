#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

from aws_cdk import App, Environment, Stack

from rag_with_aos import (
  VpcStack,
  OpenSearchStack,
  SageMakerStudioStack,
  EmbeddingEndpointStack,
  LLMEndpointStack,
  StreamlitAppStack
)

APP_ENV = Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = App()

vpc_stack = VpcStack(app, 'RAGVpcStack',
  env=APP_ENV)

ops_stack = OpenSearchStack(app, 'RAGOpenSearchStack',
  vpc_stack.vpc,
  env=APP_ENV
)
ops_stack.add_dependency(vpc_stack)

sm_studio_stack = SageMakerStudioStack(app, 'RAGSageMakerStudioStack',
  vpc_stack.vpc,
  env=APP_ENV
)
sm_studio_stack.add_dependency(ops_stack)

sm_embedding_endpoint = EmbeddingEndpointStack(app, 'EmbeddingEndpointStack',
  env=APP_ENV
)
sm_embedding_endpoint.add_dependency(sm_studio_stack)

sm_llm_endpoint = LLMEndpointStack(app, 'LLMEndpointStack',
  env=APP_ENV
)
sm_llm_endpoint.add_dependency(sm_embedding_endpoint)

ecs_app = StreamlitAppStack(app, "StreamlitAppStack",
  vpc_stack.vpc,
  ops_stack.master_user_secret,
  ops_stack.opensearch_domain,
  sm_llm_endpoint.llm_endpoint,
  sm_embedding_endpoint.embedding_endpoint,
  env=APP_ENV
)
ecs_app.add_dependency(sm_llm_endpoint)

app.synth()
