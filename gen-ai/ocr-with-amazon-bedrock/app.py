#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  ECSAlbFargateServiceStack,
  ECSClusterStack,
  ECSTaskStack,
  VpcStack
)

AWS_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

vpc_stack = VpcStack(app, "OCRAppVpcStack",
    env=AWS_ENV)

ecs_cluster_stack = ECSClusterStack(app, "OCRAppECSClusterStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
ecs_cluster_stack.add_dependency(vpc_stack)

ecs_task_stack = ECSTaskStack(app, "OCRAppECSTaskStack",
  env=AWS_ENV
)
ecs_task_stack.add_dependency(ecs_cluster_stack)

ecs_fargate_stack = ECSAlbFargateServiceStack(app, "OCRAppECSAlbFargateServiceStack",
  vpc_stack.vpc,
  ecs_cluster_stack.ecs_cluster,
  ecs_task_stack.ecs_task_definition,
  env=AWS_ENV
)
ecs_fargate_stack.add_dependency(ecs_task_stack)

app.synth()