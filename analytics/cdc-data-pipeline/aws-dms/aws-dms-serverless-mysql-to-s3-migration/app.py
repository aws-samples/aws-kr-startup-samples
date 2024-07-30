#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

from cdk_stacks import (
  VpcStack,
  AuroraMysqlStack,
  BastionHostEC2InstanceStack,
  S3Stack,
  DmsIAMRolesStack,
  DMSServerlessAuroraMysqlToS3Stack
)

import aws_cdk as cdk


APP_ENV = cdk.Environment(
  account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION')
)

app = cdk.App()

vpc_stack = VpcStack(app, 'DMSAuroraMysqlToS3VPCStack',
  env=APP_ENV
)

aurora_mysql_stack = AuroraMysqlStack(app, 'AuroraMysqlStack',
  vpc_stack.vpc,
  env=APP_ENV
)
aurora_mysql_stack.add_dependency(vpc_stack)

bastion_host = BastionHostEC2InstanceStack(app, 'AuroraMysqlBastionHost',
  vpc_stack.vpc,
  aurora_mysql_stack.sg_mysql_client,
  env=APP_ENV
)
bastion_host.add_dependency(aurora_mysql_stack)

dms_target_s3_stack = S3Stack(app, 'DMSServerlessTargetS3Stack',
  env=APP_ENV
)
dms_target_s3_stack.add_dependency(bastion_host)

dms_iam_permissions = DmsIAMRolesStack(app, 'DMSRequiredIAMRolesStack')
dms_iam_permissions.add_dependency(dms_target_s3_stack)

dms_task_stack = DMSServerlessAuroraMysqlToS3Stack(app, 'DMSServerlessAuroraMysqlToS3Stack',
  vpc_stack.vpc,
  aurora_mysql_stack.sg_mysql_client,
  aurora_mysql_stack.db_secret,
  aurora_mysql_stack.db_hostname,
  env=APP_ENV
)
dms_task_stack.add_dependency(dms_iam_permissions)

app.synth()
