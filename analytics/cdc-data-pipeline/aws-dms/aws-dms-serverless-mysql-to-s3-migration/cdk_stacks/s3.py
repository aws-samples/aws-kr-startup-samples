#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_s3 as s3,
)
from constructs import Construct


class S3Stack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    dms_data_target = self.node.try_get_context('dms_data_target')
    s3_bucket_name = dms_data_target['s3_bucket_name']
    s3_bucket = s3.Bucket(self, 's3bucket',
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: Default: core.RemovalPolicy.RETAIN - The bucket will be orphaned
      bucket_name=s3_bucket_name)

    self.s3_bucket_name = s3_bucket.bucket_name

    cdk.CfnOutput(self, 'DMSTargetS3BucketName',
      value=s3_bucket.bucket_name,
      export_name=f'{self.stack_name}-DMSTargetS3BucketName')
