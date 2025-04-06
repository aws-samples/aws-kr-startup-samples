#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import random
import string

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ecr,
)
from constructs import Construct

from cdklabs.generative_ai_cdk_constructs import (
  CustomSageMakerEndpoint,
  ContainerImage,
  SageMakerInstanceType,
)

random.seed(37)


def name_from_base(base, max_length=63):
  unique = ''.join(random.sample(string.digits, k=7))
  max_length = 63
  trimmed_base = base[: max_length - len(unique) - 1]
  return "{}-{}".format(trimmed_base, unique)


class ExaoneDeepSGLangRealtimeEndpointStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    # Need an existing bucket containing model artifacts that this construct can access
    model_data_source = self.node.try_get_context('model_data_source')

    s3_bucket_name = model_data_source['s3_bucket_name']
    s3_object_key_name = model_data_source['s3_object_key_name']
    assert s3_object_key_name.endswith('.tar.gz') or s3_object_key_name.endswith('/')

    model_data_url = f's3://{s3_bucket_name}/{s3_object_key_name}'

    model_id = self.node.try_get_context('model_id') or 'LGAI-EXAONE/EXAONE-Deep-7.8B'
    sagemaker_endpoint_name = name_from_base(model_id.lower().replace('/', '-').replace('.', '-'))

    instance_type = self.node.try_get_context('sagemaker_instance_type') or 'ml.g5.2xlarge'
    endpoint_settings = self.node.try_get_context('sagemaker_endpoint_settings') or {}

    ecr_info = self.node.try_get_context('ecr')
    ecr_repository_name = ecr_info['repository_name']
    image_tag = ecr_info.get('tag', 'latest')
    ecr_repository = aws_ecr.Repository.from_repository_name(self, "SGLangECRRepository",
      repository_name=ecr_repository_name
    )
    container = ContainerImage.from_ecr_repository(repository=ecr_repository, tag=image_tag)

    self.sagemaker_endpoint = CustomSageMakerEndpoint(self, 'SGLangSageMakerEndpoint',
      model_id=model_id,
      instance_type=SageMakerInstanceType.of(instance_type),
      container=container,
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
    cdk.CfnOutput(self, 'ECRUri',
      value=f"{ecr_repository.repository_uri}:{image_tag}",
      export_name=f'{self.stack_name}-ECRUri')