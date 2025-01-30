#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  ALBClickhouseStack,
  ECRStack,
  ECSClusterStack,
  ECSTaskClickhouseStack,
  ECSAlbFargateServiceStack,
  EFSStack,
  ServiceDiscoveryStack,
  VpcStack
)

AWS_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

ecr_stack = ECRStack(app, "ClickhouseECRStack",
  env=AWS_ENV
)

vpc_stack = VpcStack(app, "ClickhouseVpcStack",
  env=AWS_ENV
)
vpc_stack.add_dependency(ecr_stack)

service_discovery_stack = ServiceDiscoveryStack(app, "ClickhouseServiceDiscoveryStack",
  vpc_stack.vpc,
  env=AWS_ENV)
service_discovery_stack.add_dependency(vpc_stack)

alb_stack = ALBClickhouseStack(app, "ClickhouseALBStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
alb_stack.add_dependency(service_discovery_stack)

ecs_cluster_stack = ECSClusterStack(app, "ClickhouseECSClusterStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
ecs_cluster_stack.add_dependency(alb_stack)

efs_stack = EFSStack(app, "ClickhouseEFSStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
efs_stack.add_dependency(ecs_cluster_stack)

ecs_task_stack = ECSTaskClickhouseStack(app, "ClickhouseECSTaskStack",
  ecr_stack.repositories,
  efs_stack.efs_file_system,
  env=AWS_ENV
)
ecs_task_stack.add_dependency(efs_stack)

ecs_fargate_stack = ECSAlbFargateServiceStack(app, "ClickhouseECSServiceStack",
  vpc=vpc_stack.vpc,
  ecs_cluster=ecs_cluster_stack.ecs_cluster,
  ecs_task_definition=ecs_task_stack.ecs_task_definition,
  load_balancer=alb_stack.load_balancer,
  sg_efs_inbound=efs_stack.sg_efs_inbound,
  cloud_map_service=service_discovery_stack.service,
  env=AWS_ENV
)
ecs_fargate_stack.add_dependency(ecs_task_stack)

app.synth()
