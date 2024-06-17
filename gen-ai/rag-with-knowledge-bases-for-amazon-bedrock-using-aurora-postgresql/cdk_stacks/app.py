#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from rag_with_kb_aurora_pgvector import (
  AuroraPostgresqlStack,
  BedrockKnowledgeBaseStack,
  SageMakerStudioStack,
  VpcStack
)


AWS_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

vpc_stack = VpcStack(app, 'BedrockKBVpcStack',
  env=AWS_ENV
)

aurora_pgsql_stack = AuroraPostgresqlStack(app, 'BedrockKBAuroraPgVectorStack',
  vpc_stack.vpc,
  env=AWS_ENV
)
aurora_pgsql_stack.add_dependency(vpc_stack)

sm_studio_stack = SageMakerStudioStack(app, 'BedrockKBSageMakerStudioStack',
  vpc_stack.vpc,
  aurora_pgsql_stack.sg_rds_client,
  env=AWS_ENV
)
sm_studio_stack.add_dependency(aurora_pgsql_stack)

kb_for_bedrock_stack = BedrockKnowledgeBaseStack(app, 'BedrockKnowledgeBaseStack',
  aurora_pgsql_stack.rds_credentials_secret_arn,
  aurora_pgsql_stack.rds_cluster_arn,
  env=AWS_ENV
)
kb_for_bedrock_stack.add_dependency(sm_studio_stack)

app.synth()
