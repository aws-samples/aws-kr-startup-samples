#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_rds,
)
from constructs import Construct


class ZeroEtlFromAuroraMysqlToRedshifStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, rds_cluster, rss_namespace, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    zero_etl_integration_setting = self.node.try_get_context('zero_etl_integration') or {}

    INTEGRATION_NAME = f"{rds_cluster.cluster_identifier}-to-{rss_namespace.attr_namespace_namespace_name}"[:63]
    zero_etl_integration_name = zero_etl_integration_setting.get('integration_name', INTEGRATION_NAME)
    cfn_integration = aws_rds.CfnIntegration(self, "ZeroETLIntegration",
      source_arn=rds_cluster.cluster_arn,
      target_arn=rss_namespace.attr_namespace_namespace_arn,
      data_filter=zero_etl_integration_setting.get("data_filter", None),
      description="RDS MySQL to Redshift Serverless",
      integration_name=zero_etl_integration_name
    )


    cdk.CfnOutput(self, 'ZeroETLIntegrationName',
      value=cfn_integration.integration_name,
      export_name=f'{self.stack_name}-ZeroETLIntegrationName')
    cdk.CfnOutput(self, 'ZeroETLIntegrationArn',
      value=cfn_integration.attr_integration_arn,
      export_name=f'{self.stack_name}-ZeroETLIntegrationArn')
