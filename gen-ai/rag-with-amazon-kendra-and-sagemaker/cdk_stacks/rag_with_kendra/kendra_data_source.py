#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_iam,
  aws_kendra,
  aws_s3 as s3
)
from constructs import Construct

class KendraDataSourceStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, kendra_index_id, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    kendra_data_source_role_policy_doc = aws_iam.PolicyDocument()
    kendra_data_source_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": [f"arn:aws:kendra:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:index/{kendra_index_id}"],
      "actions": [
        "kendra:BatchPutDocument",
        "kendra:BatchDeleteDocument"
      ]
    }))

    kendra_data_source_role = aws_iam.Role(self, 'KendraDataSourceRole',
      role_name=f'{self.stack_name}-DocsKendraDataSourceRole',
      assumed_by=aws_iam.ServicePrincipal('kendra.amazonaws.com'),
      inline_policies={
        'DocsKendraDataSourceRolePolicy': kendra_data_source_role_policy_doc
      }
    )

    kendra_data_source_configuration = aws_kendra.CfnDataSource.DataSourceConfigurationProperty(
      web_crawler_configuration=aws_kendra.CfnDataSource.WebCrawlerConfigurationProperty(
        urls=aws_kendra.CfnDataSource.WebCrawlerUrlsProperty(
          site_maps_configuration=aws_kendra.CfnDataSource.WebCrawlerSiteMapsConfigurationProperty(
            site_maps=[
              'https://docs.aws.amazon.com/lex/latest/dg/sitemap.xml',
              'https://docs.aws.amazon.com/kendra/latest/dg/sitemap.xml',
              'https://docs.aws.amazon.com/sagemaker/latest/dg/sitemap.xml'
            ]
          )
        ),
        url_inclusion_patterns=[
          '.*https://docs.aws.amazon.com/lex/.*',
          '.*https://docs.aws.amazon.com/kendra/.*',
          '.*https://docs.aws.amazon.com/sagemaker/.*'
        ]
      )
    )

    kendra_data_source = aws_kendra.CfnDataSource(self, "KendraDataSource",
      index_id=kendra_index_id,
      name=f"{self.stack_name}-KendraDocsDS",
      type="WEBCRAWLER",
      data_source_configuration=kendra_data_source_configuration,
      role_arn=kendra_data_source_role.role_arn
    )

    self.kendra_data_source_id = kendra_data_source.attr_id

    cdk.CfnOutput(self, 'KendraDataSourceId', value=self.kendra_data_source_id,
      export_name=f"{self.stack_name}-KendraDataSourceId")
