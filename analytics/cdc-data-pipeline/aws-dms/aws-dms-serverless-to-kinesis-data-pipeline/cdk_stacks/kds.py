#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Duration,
  Stack,
  aws_kinesis
)
from constructs import Construct


class KinesisDataStreamStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    kinesis_stream_name = self.node.try_get_context('kinesis_stream_name')
    kinesis_stream = aws_kinesis.Stream(self, 'DMSTargetKinesisStream',
      retention_period=Duration.hours(24),
      stream_mode=aws_kinesis.StreamMode.ON_DEMAND,
      stream_name=kinesis_stream_name
    )

    self.kinesis_stream_name = kinesis_stream.stream_name
    self.kinesis_stream_arn = kinesis_stream.stream_arn

    cdk.CfnOutput(self, 'DMSTargetKinesisStreamName',
      value=self.kinesis_stream_name,
      export_name=f'{self.stack_name}-DMSTargetKinesisStreamName')
    cdk.CfnOutput(self, 'DMSTargetKinesisStreamArn',
      value=self.kinesis_stream_arn,
      export_name=f'{self.stack_name}-DMSTargetKinesisStreamArn')

