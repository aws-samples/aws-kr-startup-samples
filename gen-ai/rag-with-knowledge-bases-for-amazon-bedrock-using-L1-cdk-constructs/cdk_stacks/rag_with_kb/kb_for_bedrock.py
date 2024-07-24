#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_bedrock,
  aws_logs
)
from constructs import Construct


class KnowledgeBaseforBedrockStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, kb_role_arn, opensearch_collection_arn, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    bedrock_kb_configuration = self.node.try_get_context('knowledge_base_for_bedrock')
    knowledge_base_configuration = bedrock_kb_configuration['knowledge_base_configuration']['vector_knowledge_base_configuration']
    opensearch_serverless_configuration = bedrock_kb_configuration['storage_configuration']['opensearch_serverless_configuration']

    cfn_knowledge_base = aws_bedrock.CfnKnowledgeBase(self, 'CfnKnowledgeBase',
      knowledge_base_configuration=aws_bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
        type='VECTOR',
        vector_knowledge_base_configuration=aws_bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
          embedding_model_arn=knowledge_base_configuration['embedding_model_arn']
        )
      ),
      name=bedrock_kb_configuration['name'],
      role_arn=kb_role_arn,
      storage_configuration=aws_bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
        type='OPENSEARCH_SERVERLESS',
        opensearch_serverless_configuration=aws_bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
          collection_arn=opensearch_collection_arn,
          field_mapping=aws_bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
            metadata_field=opensearch_serverless_configuration['field_mapping']['metadata_field'],
            text_field=opensearch_serverless_configuration['field_mapping']['text_field'],
            vector_field=opensearch_serverless_configuration['field_mapping']['vector_field']
          ),
          vector_index_name=opensearch_serverless_configuration['vector_index_name']
        )
      ),
      description=bedrock_kb_configuration['description']
    )

    kb_log_group = aws_logs.LogGroup(self, "KBApplicationLogGroup",
      log_group_name=f"/aws/vendedlogs/bedrock/knowledge-base/APPLICATION_LOGS/{cfn_knowledge_base.name}",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: for testing
      retention=aws_logs.RetentionDays.THREE_DAYS
    )

    cfn_delivery_source = aws_logs.CfnDeliverySource(self, "CfnDeliverySourceForKB",
      name=f"{cfn_knowledge_base.name}",
      log_type="APPLICATION_LOGS",
      resource_arn=cfn_knowledge_base.attr_knowledge_base_arn,
    )

    cfn_delivery_destination = aws_logs.CfnDeliveryDestination(self, "CfnDeliveryDestinationForKB",
      name=f"{cfn_knowledge_base.name}",
      destination_resource_arn=kb_log_group.log_group_arn,
    )

    cfn_delivery = aws_logs.CfnDelivery(self, "CfnDeliveryForKB",
      delivery_destination_arn=cfn_delivery_destination.attr_arn,
      delivery_source_name=cfn_delivery_source.name,
    )
    cfn_delivery.add_dependency(cfn_delivery_source)

    self.knowledge_base_id = cfn_knowledge_base.attr_knowledge_base_id


    cdk.CfnOutput(self, 'KnowledgeBaseId',
      value=self.knowledge_base_id,
      export_name=f'{self.stack_name}-KnowledgeBaseId')
    cdk.CfnOutput(self, 'KnowledgeBaseRoleArn',
      value=cfn_knowledge_base.role_arn,
      export_name=f'{self.stack_name}-KnowledgeBaseRoleArn')
    cdk.CfnOutput(self, 'KnowledgeBaseName',
      value=cfn_knowledge_base.name,
      export_name=f'{self.stack_name}-KnowledgeBaseName')
    cdk.CfnOutput(self, 'KnowledgeVectorIndexName',
      value=cfn_knowledge_base.storage_configuration.opensearch_serverless_configuration.vector_index_name,
      export_name=f'{self.stack_name}-KnowledgeVectorIndexName')