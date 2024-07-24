#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import random
import string

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_s3 as s3,
  aws_logs
)
from constructs import Construct

from cdklabs.generative_ai_cdk_constructs import bedrock

random.seed(47)


class BedrockKnowledgeBaseStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    S3_BUCKET_SUFFIX = ''.join(random.sample((string.ascii_lowercase + string.digits), k=7))
    S3_DEFAULT_BUCKET_NAME = f'kb-for-amazon-bedrock-{cdk.Aws.REGION}-{S3_BUCKET_SUFFIX}'

    s3_bucket_name = self.node.try_get_context('s3_bucket_name') or S3_DEFAULT_BUCKET_NAME
    s3_bucket = s3.Bucket(self, "s3bucket",
      bucket_name=s3_bucket_name,
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: Default: core.RemovalPolicy.RETAIN - The bucket will be orphaned
      auto_delete_objects=True)

    kb_for_bedrock = bedrock.KnowledgeBase(self, 'KnowledgeBaseForBedrock',
      embeddings_model=bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V1
    )

    kb_data_source_name = self.node.try_get_context('knowledge_base_data_source_name')
    kb_data_source = bedrock.S3DataSource(self, 'KnowledgeBaseDataSource',
      bucket=s3_bucket,
      data_source_name=kb_data_source_name,
      knowledge_base=kb_for_bedrock,
      chunking_strategy=bedrock.ChunkingStrategy.FIXED_SIZE,
      max_tokens=500,
      overlap_percentage=20
    )

    kb_log_group = aws_logs.LogGroup(self, "KBApplicationLogGroup",
      log_group_name=f"/aws/vendedlogs/bedrock/knowledge-base/APPLICATION_LOGS/{kb_for_bedrock.name}",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: for testing
      retention=aws_logs.RetentionDays.THREE_DAYS
    )

    cfn_delivery_source = aws_logs.CfnDeliverySource(self, "CfnDeliverySourceForKB",
      name=f"{kb_for_bedrock.name}",
      log_type="APPLICATION_LOGS",
      resource_arn=kb_for_bedrock.knowledge_base_arn,
    )

    cfn_delivery_destination = aws_logs.CfnDeliveryDestination(self, "CfnDeliveryDestinationForKB",
      name=f"{kb_for_bedrock.name}",
      destination_resource_arn=kb_log_group.log_group_arn,
    )

    cfn_delivery = aws_logs.CfnDelivery(self, "CfnDeliveryForKB",
      delivery_destination_arn=cfn_delivery_destination.attr_arn,
      delivery_source_name=cfn_delivery_source.name,
    )
    cfn_delivery.add_dependency(cfn_delivery_source)


    cdk.CfnOutput(self, 'KnowledgeBaseId',
      value=kb_for_bedrock.knowledge_base_id,
      export_name=f'{self.stack_name}-KnowledgeBaseId')
    cdk.CfnOutput(self, 'KnowledgeBaseName',
      value=kb_for_bedrock.name,
      export_name=f'{self.stack_name}-KnowledgeBaseName')
    cdk.CfnOutput(self, 'DataSourceId',
      value=kb_data_source.data_source_id,
      export_name=f'{self.stack_name}-DataSourceId')
    cdk.CfnOutput(self, 'DataSourceName',
      value=kb_data_source.data_source_id,
      export_name=f'{self.stack_name}-DataSourceName')
