#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  VpcStack,
  BastionHostStack,
  KinesisDataStreamsStack,
  LambdaLayersStack,
  LambdaFunctionStack,
  MemoryDBAclStack,
  MemoryDBStack
)


APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

vpc_stack = VpcStack(app, 'MemoryDBVPCStack',
  env=APP_ENV)

memorydb_acl_stack = MemoryDBAclStack(app, 'MemoryDBAclStack',
  env=APP_ENV)

memorydb_stack = MemoryDBStack(app, 'MemoryDBStack',
  vpc_stack.vpc,
  memorydb_acl_stack.memorydb_acl,
  env=APP_ENV)
memorydb_stack.add_dependency(memorydb_acl_stack)

kds_stack = KinesisDataStreamsStack(app, 'KinesisDataStreamsStack',
  env=APP_ENV
)
kds_stack.add_dependency(memorydb_acl_stack)

lambda_layers_stack = LambdaLayersStack(app, 'LambdaLayersStack',
  env=APP_ENV
)
lambda_layers_stack.add_dependency(kds_stack)

lambda_function_stack = LambdaFunctionStack(app, 'LambdaFunctionStack',
  vpc_stack.vpc,
  kds_stack.source_kinesis_stream,
  lambda_layers_stack.lambda_layers,
  memorydb_stack.memorydb_endpoint,
  memorydb_acl_stack.memorydb_secret_name,
  memorydb_stack.sg_memorydb_client,
  env=APP_ENV
)
lambda_function_stack.add_dependency(lambda_layers_stack)

bastion_host_stack = BastionHostStack(app, 'BastionHostStack',
  vpc_stack.vpc,
  memorydb_stack.sg_memorydb_client,
  env=APP_ENV)
bastion_host_stack.add_dependency(lambda_function_stack)

app.synth()
