#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

from rag_with_kendra import (
  KendraIndexStack,
  KendraDataSourceStack,
  KendraDataSourceSyncLambdaStack,
  KendraDataSourceSyncStack,
  VpcStack,
  SageMakerStudioStack,
  LLMEndpointStack
)

import aws_cdk as cdk

AWS_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION'))

app = cdk.App()

kendra_index = KendraIndexStack(app, "RAGwithKendraIndexStack",
  env=AWS_ENV)

kendra_data_source = KendraDataSourceStack(app, "RAGwithKendraDataSourceStack",
  kendra_index_id=kendra_index.kendra_index_id,
  env=AWS_ENV)
kendra_data_source.add_dependency(kendra_index)

kendra_data_source_sync_lambda = KendraDataSourceSyncLambdaStack(app, "RAGwithKendraDSSyncLambdaStack",
  kendra_index_id=kendra_index.kendra_index_id,
  kendra_data_source_id=kendra_data_source.kendra_data_source_id,
  env=AWS_ENV)
kendra_data_source_sync_lambda.add_dependency(kendra_data_source)

kendra_data_source_sync = KendraDataSourceSyncStack(app, "RAGwithKendraDSSyncStack",
  kendra_data_source_sync_lambda.kendra_ds_sync_lambda_arn,
  env=AWS_ENV)
kendra_data_source_sync.add_dependency(kendra_data_source_sync_lambda)

vpc_stack = VpcStack(app, 'RAGwithKendraVpcStack',
  env=AWS_ENV)
vpc_stack.add_dependency(kendra_data_source_sync)

sm_studio_stack = SageMakerStudioStack(app, 'RAGwithKendraSageMakerStudioStack',
  vpc_stack.vpc,
  env=AWS_ENV)
sm_studio_stack.add_dependency(vpc_stack)

sm_llm_endpoint = LLMEndpointStack(app, 'RAGwithKendraLLMEndpointStack',
  sm_studio_stack.sm_execution_role,
  env=AWS_ENV)
sm_llm_endpoint.add_dependency(sm_studio_stack)

app.synth()
