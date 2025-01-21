#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  VpcStack,
  AuroraMysqlStack,
  RedshiftServerlessStack,
  ZeroEtlFromAuroraMysqlToRedshifStack,
  BastionHostEC2InstanceStack
)


APP_ENV = cdk.Environment(
  account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION')
)

app = cdk.App()

vpc_stack = VpcStack(app, 'AuroraMySQLVpcStack',
  env=APP_ENV)

aurora_mysql_stack = AuroraMysqlStack(app, 'AuroraMySQLStack',
  vpc_stack.vpc,
  env=APP_ENV
)
aurora_mysql_stack.add_dependency(vpc_stack)

bastion_host = BastionHostEC2InstanceStack(app, 'AuroraMySQLClientHostStack',
  vpc_stack.vpc,
  aurora_mysql_stack.sg_mysql_client,
  env=APP_ENV
)
bastion_host.add_dependency(aurora_mysql_stack)

rss_stack = RedshiftServerlessStack(app, 'RedshiftServerlessStack',
  vpc_stack.vpc,
  env=APP_ENV
)
rss_stack.add_dependency(bastion_host)

zero_etl_integration = ZeroEtlFromAuroraMysqlToRedshifStack(
  app,
  'ZeroETLfromRDStoRSS',
  aurora_mysql_stack.rds_cluster,
  rss_stack.rss_namespace,
  env=APP_ENV
)
zero_etl_integration.add_dependency(rss_stack)

app.synth()

