#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import random
import string

import aws_cdk as cdk

from aws_cdk import (
  Stack
)
from constructs import Construct

from cdklabs.generative_ai_cdk_constructs import (
  CustomSageMakerEndpoint,
  DeepLearningContainerImage,
  SageMakerInstanceType,
)

random.seed(47)


class EmbeddingEndpointStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    bucket_name = f'jumpstart-cache-prod-{cdk.Aws.REGION}'
    key_name = 'huggingface-infer/prepack/v1.0.0/infer-prepack-huggingface-textembedding-gpt-j-6b-fp16.tar.gz'

    RANDOM_GUID = ''.join(random.sample(string.digits, k=7))
    endpoint_name = f"gpt-j-6b-fp16-endpoint-{RANDOM_GUID}"

    #XXX: https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/src/patterns/gen-ai/aws-model-deployment-sagemaker/README_custom_sagemaker_endpoint.md
    self.embedding_endpoint = CustomSageMakerEndpoint(self, 'EmbeddingEndpoint',
      model_id='gpt-j-6b-fp16',
      instance_type=SageMakerInstanceType.ML_G5_2_XLARGE,
      container=DeepLearningContainerImage.from_deep_learning_container_image(
        'pytorch-inference',
        '1.12.0-gpu-py38'
      ),
      model_data_url=f's3://{bucket_name}/{key_name}',
      endpoint_name=endpoint_name,
      instance_count=1,
      # volume_size_in_gb=100
    )

    cdk.CfnOutput(self, 'EmbeddingEndpointName',
      value=self.embedding_endpoint.cfn_endpoint.endpoint_name,
      export_name=f'{self.stack_name}-EmbeddingEndpointName')
    cdk.CfnOutput(self, 'EmbeddingEndpointArn',
      value=self.embedding_endpoint.endpoint_arn,
      export_name=f'{self.stack_name}-EmbeddingEndpointArn')
