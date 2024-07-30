#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_lambda,
  aws_s3 as s3,
  aws_logs
)
from constructs import Construct


class LambdaLayersStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    S3_BUCKET_LAMBDA_LAYER_LIB = self.node.try_get_context('s3_bucket_lambda_layer_lib')
    s3_lib_bucket = s3.Bucket.from_bucket_name(self, "LambdaLayerS3Bucket",
      S3_BUCKET_LAMBDA_LAYER_LIB)

    redis_lib_layer = aws_lambda.LayerVersion(self, "RedisLib",
      layer_version_name="redis-py-cluster-lib",
      compatible_runtimes=[aws_lambda.Runtime.PYTHON_3_11],
      code=aws_lambda.Code.from_bucket(s3_lib_bucket, "var/redis-py-cluster-lib.zip")
    )

    self.lambda_layers = [redis_lib_layer]


    cdk.CfnOutput(self, 'LayerVersionArn',
      value=redis_lib_layer.layer_version_arn,
      export_name=f'{self.stack_name}-LayerVersionArn')
