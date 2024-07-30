#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_iam,
  aws_lambda,
  aws_logs
)
from constructs import Construct

from aws_cdk.aws_lambda_event_sources import (
  KinesisEventSource
)


class LambdaFunctionStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
               vpc,
               source_kinesis_stream,
               lambda_layers,
               memorydb_endpoint,
               memorydb_secret_name,
               sg_memorydb_client,
               **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    lambda_fn = aws_lambda.Function(self, "UVCounterLambda",
      runtime=aws_lambda.Runtime.PYTHON_3_11,
      function_name="UVCounter",
      handler="uv_counter.lambda_handler",
      description="Count unique visitors with HyperLogLog",
      code=aws_lambda.Code.from_asset(os.path.join(os.path.dirname(__file__), '../src/main/python/UVCounter')),
      environment={
        'REDIS_HOST': memorydb_endpoint,
        'MEMORYDB_SECRET_NAME': memorydb_secret_name,
        'REGION_NAME': kwargs['env'].region,
      },
      timeout=cdk.Duration.minutes(5),
      layers=lambda_layers,
      security_groups=[sg_memorydb_client],
      vpc=vpc
    )

    lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["arn:aws:secretsmanager:*:*:*"],
      actions=["secretsmanager:GetSecretValue"])
    )

    kinesis_event_source = KinesisEventSource(source_kinesis_stream,
      batch_size=1000, starting_position=aws_lambda.StartingPosition.LATEST)
    lambda_fn.add_event_source(kinesis_event_source)

    log_group = aws_logs.LogGroup(self, "UVCounterLogGroup",
      log_group_name=f"/aws/lambda/UVCounter",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: for testing
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(lambda_fn)


    cdk.CfnOutput(self, 'LambdaRoleArn',
      value=lambda_fn.role.role_arn,
      export_name=f'{self.stack_name}-LambdaRoleArn')
