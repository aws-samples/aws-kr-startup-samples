#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  VpcStack,
  AuroraMysqlStack,
  KinesisDataStreamStack,
  DmsIAMRolesStack,
  DMSAuroraMysqlToKinesisStack,
  FirehoseToIcebergStack,
  FirehoseRoleStack,
  FirehoseDataProcLambdaStack,
  DataLakePermissionsStack,
  S3BucketStack,
  BastionHostEC2InstanceStack
)

APP_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION'))

app = cdk.App()

vpc_stack = VpcStack(app, 'TransactionalDataLakeVpc', env=APP_ENV)

aurora_mysql_stack = AuroraMysqlStack(app, 'AuroraMysqlAsDMSDataSource',
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

kds_stack = KinesisDataStreamStack(app, 'DMSTargetKinesisDataStream')
kds_stack.add_dependency(aurora_mysql_stack)

dms_iam_permissions = DmsIAMRolesStack(app, 'DMSRequiredIAMRolesStack')
dms_iam_permissions.add_dependency(kds_stack)

dms_stack = DMSAuroraMysqlToKinesisStack(app, 'DMSTaskAuroraMysqlToKinesis',
  vpc_stack.vpc,
  aurora_mysql_stack.sg_mysql_client,
  aurora_mysql_stack.rds_credentials,
  kds_stack.kinesis_stream.stream_arn,
  env=APP_ENV
)
dms_stack.add_dependency(dms_iam_permissions)

s3_dest_bucket = S3BucketStack(app, 'DataFirehoseToIcebergS3Path',
  env=APP_ENV
)
s3_dest_bucket.add_dependency(dms_stack)

firehose_data_transform_lambda = FirehoseDataProcLambdaStack(app,
  'FirehoseDataTransformLambdaStack',
  env=APP_ENV
)
firehose_data_transform_lambda.add_dependency(s3_dest_bucket)

firehose_role = FirehoseRoleStack(app, 'FirehoseToIcebergRoleStack',
  firehose_data_transform_lambda.data_proc_lambda_fn,
  kds_stack.kinesis_stream,
  s3_dest_bucket.s3_bucket,
  env=APP_ENV
)
firehose_role.add_dependency(firehose_data_transform_lambda)

grant_lake_formation_permissions = DataLakePermissionsStack(app, 'GrantLFPermissionsOnFirehoseRole',
  firehose_role.firehose_role,
  env=APP_ENV
)
grant_lake_formation_permissions.add_dependency(firehose_role)

firehose_stack = FirehoseToIcebergStack(app, 'FirehoseToIcebergStack',
  firehose_data_transform_lambda.data_proc_lambda_fn,
  kds_stack.kinesis_stream,
  s3_dest_bucket.s3_bucket,
  firehose_role.firehose_role,
  env=APP_ENV
)
firehose_stack.add_dependency(grant_lake_formation_permissions)

app.synth()
