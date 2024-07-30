#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_stacks import (
  VpcStack,
  AuroraMysqlStack,
  KinesisDataStreamStack,
  DmsIAMRolesStack,
  DMSAuroraMysqlToKinesisStack,
  GlueJobRoleStack,
  GlueStreamDataSchemaStack,
  GlueStreamingJobStack,
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
  aurora_mysql_stack.db_hostname,
  kds_stack.kinesis_stream.stream_arn,
  env=APP_ENV
)
dms_stack.add_dependency(dms_iam_permissions)

s3_bucket = S3BucketStack(app, 'GlueStreamingCDCtoIcebergS3Path')
s3_bucket.add_dependency(dms_stack)

glue_job_role = GlueJobRoleStack(app, 'GlueStreamingCDCtoIcebergJobRole')
glue_job_role.add_dependency(s3_bucket)

glue_stream_schema = GlueStreamDataSchemaStack(app, 'GlueTableSchemaOnKinesisStream',
  kds_stack.kinesis_stream
)
glue_stream_schema.add_dependency(glue_job_role)

grant_lake_formation_permissions = DataLakePermissionsStack(app, 'GrantLFPermissionsOnGlueJobRole',
  glue_job_role.glue_job_role
)
grant_lake_formation_permissions.add_dependency(glue_job_role)
grant_lake_formation_permissions.add_dependency(glue_stream_schema)

glue_streaming_job = GlueStreamingJobStack(app, 'GlueStreamingCDCtoIceberg',
  glue_job_role.glue_job_role,
  kds_stack.kinesis_stream
)
glue_streaming_job.add_dependency(grant_lake_formation_permissions)

app.synth()
