#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_athena,
  aws_s3 as s3,
)
from constructs import Construct


class AthenaWorkGroupStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    athena_config = self.node.try_get_context('athena')

    S3_DEFAULT_BUCKET_NAME = 'aws-athena-query-results-{region}-{account_id}'.format(
        region=cdk.Aws.REGION, account_id=cdk.Aws.ACCOUNT_ID)
    s3_bucket_name = athena_config.get('query_results_s3_bucket', S3_DEFAULT_BUCKET_NAME)
    s3_bucket = s3.Bucket(self, "s3bucket",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: Default: core.RemovalPolicy.RETAIN - The bucket will be orphaned
      bucket_name=s3_bucket_name)

    ATHENA_WORK_GROUP_NAME = athena_config['work_group_name']

    athena_cfn_work_group = aws_athena.CfnWorkGroup(self, 'AthenaCfnWorkGroup',
      name=ATHENA_WORK_GROUP_NAME,

      # the properties below are optional
      description='workgroup for developer',
      recursive_delete_option=False,
      state='ENABLED', # [DISABLED, ENABLED]
      tags=[cdk.CfnTag(
        key='Name',
        value=ATHENA_WORK_GROUP_NAME
      )],
      work_group_configuration=aws_athena.CfnWorkGroup.WorkGroupConfigurationProperty(
        #XXX: EnforceWorkGroupConfiguration
        # Link: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-athena-workgroup-workgroupconfiguration.html#cfn-athena-workgroup-workgroupconfiguration-enforceworkgroupconfiguration
        # If set to "true", the settings for the workgroup override client-side settings.
        # If set to "false", client-side settings are used.
        enforce_work_group_configuration=False,
        # For more information about Amazon Athena engine version,
        # see https://docs.aws.amazon.com/athena/latest/ug/engine-versions-reference.html
        engine_version=aws_athena.CfnWorkGroup.EngineVersionProperty(
          effective_engine_version='Athena engine version 3',
          selected_engine_version='Athena engine version 3'
        ),
        publish_cloud_watch_metrics_enabled=True,
        requester_pays_enabled=True,
        result_configuration=aws_athena.CfnWorkGroup.ResultConfigurationProperty(
          output_location=s3_bucket.s3_url_for_object()
        )
      )
    )

    self.athena_work_group_name = athena_cfn_work_group.name

    cdk.CfnOutput(self, 'f{self.stack_name}_AthenaWorkGroupName', value=self.athena_work_group_name,
      export_name=f'{self.stack_name}-AthenaWorkGroupName')

