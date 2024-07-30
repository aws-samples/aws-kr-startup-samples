#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_stacks import (
  VpcStack,
  AuroraMysqlStack,
  KinesisDataStreamStack,
  DmsIAMRolesStack,
  DMSAuroraMysqlToKinesisStack,
  OpenSearchStack,
  KinesisFirehoseStack,
  BastionHostEC2InstanceStack,
)

APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

vpc_stack = VpcStack(app, 'VpcStack',
  env=APP_ENV)

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

kds_stack = KinesisDataStreamStack(app, 'DMSTargetKinesisDataStreamStack')
kds_stack.add_dependency(bastion_host)

dms_iam_permissions = DmsIAMRolesStack(app, 'DMSRequiredIAMRolesStack')
dms_iam_permissions.add_dependency(kds_stack)

dms_stack = DMSAuroraMysqlToKinesisStack(app, 'DMSAuroraMysqlToKinesisStack',
  vpc_stack.vpc,
  aurora_mysql_stack.sg_mysql_client,
  aurora_mysql_stack.db_secret,
  aurora_mysql_stack.db_hostname,
  kds_stack.kinesis_stream_arn,
  env=APP_ENV
)
dms_stack.add_dependency(dms_iam_permissions)

ops_stack = OpenSearchStack(app, 'OpenSearchStack',
  vpc_stack.vpc,
  bastion_host.sg_bastion_host,
  env=APP_ENV
)
ops_stack.add_dependency(dms_stack)

firehose_stack = KinesisFirehoseStack(app, 'FirehoseStack',
  vpc_stack.vpc,
  kds_stack.kinesis_stream_arn,
  ops_stack.ops_domain_arn,
  ops_stack.ops_client_sg_id,
  env=APP_ENV
)
firehose_stack.add_dependency(ops_stack)

app.synth()
