#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import random
import string

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_s3 as s3,
)
from constructs import Construct

from cdklabs.generative_ai_cdk_constructs import (
  bedrock,
  amazonaurora
)

random.seed(47)


class BedrockKnowledgeBaseStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, rds_credentials_secret_arn, rds_cluster_arn, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    aurora_postgresql = amazonaurora.AmazonAuroraVectorStore(
      credentials_secret_arn=rds_credentials_secret_arn,
      resource_arn=rds_cluster_arn,
      # database_name='bedrock_vector_db', #XXX: What is used for? Can we change it?
      database_name='postgres',
      metadata_field='metadata',
      primary_key_field='id',
      table_name='bedrock_integration.bedrock_kb',
      text_field='chunks',
      vector_field='embedding',
    )

    kb_for_bedrock = bedrock.KnowledgeBase(self, 'KnowledgeBaseForBedrock',
      vector_store= aurora_postgresql,
      embeddings_model=bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V1
    )

    S3_BUCKET_SUFFIX = ''.join(random.sample((string.ascii_lowercase + string.digits), k=7))
    S3_DEFAULT_BUCKET_NAME = f'kb-for-amazon-bedrock-{cdk.Aws.REGION}-{S3_BUCKET_SUFFIX}'

    s3_bucket_name = self.node.try_get_context('s3_bucket_name') or S3_DEFAULT_BUCKET_NAME
    s3_bucket = s3.Bucket(self, "s3bucket",
      bucket_name=s3_bucket_name,
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: Default: core.RemovalPolicy.RETAIN - The bucket will be orphaned
      auto_delete_objects=True
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

    cdk.CfnOutput(self, 'KnowledgeBaseId',
      value=kb_for_bedrock.knowledge_base_id,
      export_name=f'{self.stack_name}-KnowledgeBaseId')
    cdk.CfnOutput(self, 'KnowledgeBaseName',
      value=kb_for_bedrock.knowledge_base_id,
      export_name=f'{self.stack_name}-KnowledgeBaseName')
    cdk.CfnOutput(self, 'DataSourceId',
      value=kb_data_source.data_source_id,
      export_name=f'{self.stack_name}-DataSourceId')
    cdk.CfnOutput(self, 'DataSourceName',
      value=kb_data_source.data_source_id,
      export_name=f'{self.stack_name}-DataSourceName')
