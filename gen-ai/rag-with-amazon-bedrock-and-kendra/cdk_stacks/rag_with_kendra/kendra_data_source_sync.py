#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack
)
from constructs import Construct


class KendraDataSourceSyncStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, data_source_sync_lambda_arn, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    kendra_data_source_sync_resource = cdk.CustomResource(self, "KendraDataSourceSync",
      service_token=data_source_sync_lambda_arn)