#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_stacks import (
  VpcStack,
  AuroraMysqlStack,
  MSKProvisionedStack,
  KafkaConnectorStack,
  GlueCatalogDatabaseStack,
  GlueMSKConnectionStack,
  GlueJobRoleStack,
  GlueStreamingJobStack,
  DataLakePermissionsStack,
  S3BucketStack,
  BastionHostEC2InstanceStack
)

APP_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION'))

app = cdk.App()

vpc_stack = VpcStack(app, 'TrxDataLakeVpc', env=APP_ENV)

aurora_mysql_stack = AuroraMysqlStack(app, 'AuroraMysqlAsDataSource',
  vpc_stack.vpc,
  env=APP_ENV
)
aurora_mysql_stack.add_dependency(vpc_stack)

msk_stack = MSKProvisionedStack(app, 'MSKAsGlueStreamingJobDataSource',
  vpc_stack.vpc,
  env=APP_ENV
)
msk_stack.add_dependency(aurora_mysql_stack)

bastion_host = BastionHostEC2InstanceStack(app, 'TrxDataLakeBastionHost',
  vpc_stack.vpc,
  aurora_mysql_stack.sg_mysql_client,
  msk_stack.sg_msk_client,
  msk_stack.msk_cluster_name,
  env=APP_ENV
)
bastion_host.add_dependency(msk_stack)

s3_bucket = S3BucketStack(app, 'GlueStreamingCDCtoIcebergS3Path')
s3_bucket.add_dependency(bastion_host)

glue_msk_connection = GlueMSKConnectionStack(app, 'GlueMSKConnection',
  vpc_stack.vpc,
  msk_stack.msk_cluster_name,
  msk_stack.sg_msk_client,
  env=APP_ENV
)
glue_msk_connection.add_dependency(msk_stack)

glue_job_role = GlueJobRoleStack(app, 'GlueStreamingMSKtoIcebergJobRole',
  msk_stack.msk_cluster_name,
)
glue_job_role.add_dependency(msk_stack)

glue_database = GlueCatalogDatabaseStack(app, 'GlueIcebergDatabase')

grant_lake_formation_permissions = DataLakePermissionsStack(app, 'GrantLFPermissionsOnGlueJobRole',
  glue_job_role.glue_job_role
)
grant_lake_formation_permissions.add_dependency(glue_database)
grant_lake_formation_permissions.add_dependency(glue_job_role)

glue_streaming_job = GlueStreamingJobStack(app, 'GlueStreamingJobMSKtoIceberg',
  glue_job_role.glue_job_role,
  glue_msk_connection.msk_connection_info
)
glue_streaming_job.add_dependency(grant_lake_formation_permissions)

msk_connector_stack = KafkaConnectorStack(app, 'KafkaConnectorStack',
  vpc_stack.vpc,
  aurora_mysql_stack.db_hostname,
  aurora_mysql_stack.sg_mysql_client,
  aurora_mysql_stack.rds_credentials,
  msk_stack.msk_cluster_name,
  msk_stack.msk_broker_node_group_info,
  env=APP_ENV
)
msk_connector_stack.add_dependency(glue_streaming_job)

app.synth()
