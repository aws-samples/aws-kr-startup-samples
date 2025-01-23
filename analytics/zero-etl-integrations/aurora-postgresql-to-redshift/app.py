#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  VpcStack,
  AuroraPostgresqlStack,
  RedshiftServerlessStack,
  ZeroEtlFromAuroraPostgresqlToRedshifStack,
  BastionHostEC2InstanceStack
)


APP_ENV = cdk.Environment(
  account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION')
)

app = cdk.App()

vpc_stack = VpcStack(app, 'AuroraPostgresVpcStack',
  env=APP_ENV)

aurora_postgresql_stack = AuroraPostgresqlStack(app, 'AuroraPostgresStack',
  vpc_stack.vpc,
  env=APP_ENV
)
aurora_postgresql_stack.add_dependency(vpc_stack)

bastion_host = BastionHostEC2InstanceStack(app, 'AuroraPostgresClientHostStack',
  vpc_stack.vpc,
  aurora_postgresql_stack.sg_postgresql_client,
  env=APP_ENV
)
bastion_host.add_dependency(aurora_postgresql_stack)

rss_stack = RedshiftServerlessStack(app, 'RedshiftServerlessStack',
  vpc_stack.vpc,
  env=APP_ENV
)
rss_stack.add_dependency(bastion_host)

zero_etl_integration = ZeroEtlFromAuroraPostgresqlToRedshifStack(
  app,
  'ZeroETLfromRDStoRSS',
  aurora_postgresql_stack.rds_cluster,
  rss_stack.rss_namespace,
  env=APP_ENV
)
zero_etl_integration.add_dependency(rss_stack)

app.synth()

