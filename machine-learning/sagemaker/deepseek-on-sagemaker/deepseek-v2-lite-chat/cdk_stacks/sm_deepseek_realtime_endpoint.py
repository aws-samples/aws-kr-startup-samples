#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import random
import string

import aws_cdk as cdk

from aws_cdk import (
  Stack,
)
from constructs import Construct

from cdklabs.generative_ai_cdk_constructs import (
  CustomSageMakerEndpoint,
  DeepLearningContainerImage,
  SageMakerInstanceType,
)

random.seed(37)


def name_from_base(base, max_length=63):
  unique = ''.join(random.sample(string.digits, k=7))
  max_length = 63
  trimmed_base = base[: max_length - len(unique) - 1]
  return "{}-{}".format(trimmed_base, unique)


class DeepSeekV2LiteChatRealtimeEndpointStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    # Need an existing bucket containing model artifacts that this construct can access
    model_data_source = self.node.try_get_context('model_data_source')

    s3_bucket_name = model_data_source['s3_bucket_name']
    s3_object_key_name = model_data_source['s3_object_key_name']
    assert s3_object_key_name.endswith('.tar.gz') or s3_object_key_name.endswith('/')

    model_data_url = f's3://{s3_bucket_name}/{s3_object_key_name}'

    model_id = self.node.try_get_context('model_id') or 'deepseek-ai/DeepSeek-V2-Lite-Chat'
    sagemaker_endpoint_name = name_from_base(model_id.lower().replace('/', '-').replace('.', '-'))

    instance_type = self.node.try_get_context('sagemaker_instance_type') or 'ml.g5.12xlarge'
    endpoint_settings = self.node.try_get_context('sagemaker_endpoint_settings') or {}

    self.sagemaker_endpoint = CustomSageMakerEndpoint(self, 'DJLSageMakerEndpoint',
      model_id=model_id,
      instance_type=SageMakerInstanceType.of(instance_type),
      # XXX: Available Deep Learing Container (DLC) Image List
      # https://github.com/aws/deep-learning-containers/blob/master/available_images.md
      # e.g., '763104351884.dkr.ecr.us-east-1.amazonaws.com/djl-inference:0.30.0-lmi12.0.0-cu124'
      container=DeepLearningContainerImage.from_deep_learning_container_image('djl-inference', '0.30.0-lmi12.0.0-cu124'),
      model_data_url=model_data_url,
      endpoint_name=sagemaker_endpoint_name,
      **endpoint_settings
    )


    cdk.CfnOutput(self, 'ModelName',
      value=self.sagemaker_endpoint.model_id,
      export_name=f'{self.stack_name}-ModelName')
    cdk.CfnOutput(self, 'EndpointName',
      value=self.sagemaker_endpoint.cfn_endpoint.endpoint_name,
      export_name=f'{self.stack_name}-EndpointName')
    cdk.CfnOutput(self, 'EndpointArn',
      value=self.sagemaker_endpoint.endpoint_arn,
      export_name=f'{self.stack_name}-EndpointArn')