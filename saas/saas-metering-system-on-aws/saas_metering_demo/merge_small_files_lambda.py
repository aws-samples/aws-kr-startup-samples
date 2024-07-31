#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_iam,
  aws_lambda,
  aws_logs,
  aws_events,
  aws_events_targets
)
from constructs import Construct

class MergeSmallFilesLambdaStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, s3_bucket_name, s3_folder_name, athena_work_group, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    _lambda_env = self.node.try_get_context('merge_small_files_lambda_env')

    LAMBDA_ENV_VARS = [
      'OLD_DATABASE',
      'OLD_TABLE_NAME',
      'NEW_DATABASE',
      'NEW_TABLE_NAME',
      'ATHENA_WORK_GROUP',
      'OLD_TABLE_LOCATION_PREFIX',
      'OUTPUT_PREFIX',
      'STAGING_OUTPUT_PREFIX',
      'COLUMN_NAMES'
    ]

    lambda_fn_env = {k: v for k, v in _lambda_env.items() if k in LAMBDA_ENV_VARS}
    additional_lambda_fn_env = {
      'ATHENA_WORK_GROUP': athena_work_group,
      'OLD_TABLE_LOCATION_PREFIX': f"s3://{os.path.join(s3_bucket_name, s3_folder_name)}",
      'OUTPUT_PREFIX': f"s3://{os.path.join(s3_bucket_name, _lambda_env['NEW_TABLE_S3_FOLDER_NAME'])}",
      'STAGING_OUTPUT_PREFIX': f"s3://{os.path.join(s3_bucket_name, 'tmp')}",
      'REGION_NAME': cdk.Aws.REGION
    }
    lambda_fn_env.update(additional_lambda_fn_env)

    self.s3_json_location, self.s3_parquet_location = (lambda_fn_env['OLD_TABLE_LOCATION_PREFIX'], lambda_fn_env['OUTPUT_PREFIX'])

    merge_small_files_lambda_fn = aws_lambda.Function(self, "MergeSmallFiles",
      runtime=aws_lambda.Runtime.PYTHON_3_9,
      function_name="MergeSmallFilesWithAthenaCTAS",
      handler="athena_ctas.lambda_handler",
      description="Merge small files in S3 with Athena CTAS query",
      code=aws_lambda.Code.from_asset('./src/main/python/MergeSmallFiles'),
      environment=lambda_fn_env,
      timeout=cdk.Duration.minutes(10)
    )

    merge_small_files_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["athena:*"]))

    merge_small_files_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["s3:Get*",
        "s3:List*",
        "s3:AbortMultipartUpload",
        "s3:PutObject",
      ]))

    merge_small_files_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["glue:CreateDatabase",
        "glue:DeleteDatabase",
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:UpdateDatabase",
        "glue:CreateTable",
        "glue:DeleteTable",
        "glue:BatchDeleteTable",
        "glue:UpdateTable",
        "glue:GetTable",
        "glue:GetTables",
        "glue:BatchCreatePartition",
        "glue:CreatePartition",
        "glue:DeletePartition",
        "glue:BatchDeletePartition",
        "glue:UpdatePartition",
        "glue:GetPartition",
        "glue:GetPartitions",
        "glue:BatchGetPartition"
      ]))

    merge_small_files_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["lakeformation:GetDataAccess"]))

    lambda_fn_target = aws_events_targets.LambdaFunction(merge_small_files_lambda_fn)
    aws_events.Rule(self, "ScheduleRule",
      schedule=aws_events.Schedule.cron(minute="10"),
      targets=[lambda_fn_target]
    )

    log_group = aws_logs.LogGroup(self, "MergeSmallFilesLogGroup",
      log_group_name=f"/aws/lambda/{self.stack_name}/MergeSmallFiles",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: for testing
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(merge_small_files_lambda_fn)

    self.lambda_exec_role = merge_small_files_lambda_fn.role

    cdk.CfnOutput(self, f'{self.stack_name}_MergeFilesFuncName',
      value=merge_small_files_lambda_fn.function_name,
      export_name=f'{self.stack_name}-MergeFilesLambdaFuncName')

    cdk.CfnOutput(self, f'{self.stack_name}_LambdaExecRoleArn',
      value=merge_small_files_lambda_fn.role.role_arn)

