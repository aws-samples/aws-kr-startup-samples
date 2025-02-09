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
  JumpStartSageMakerEndpoint,
  JumpStartModel,
  SageMakerInstanceType
)

random.seed(47)


def name_from_base(base, max_length=63):
  unique = ''.join(random.sample(string.digits, k=7))
  max_length = min(max_length, 63 - len('jumpstart-'))
  trimmed_base = base[: max_length - len(unique) - 1]
  return "{}-{}".format(trimmed_base, unique)


class DeepSeekR1JumpStartEndpointStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    jumpstart_model = self.node.try_get_context('jumpstart_model_info')
    model_id, model_version = jumpstart_model.get('model_id', 'deepseek-llm-r1-distill-qwen-32b'), jumpstart_model.get('version', '1.0.0')
    model_version = model_version if model_version != "*" else '1.0.0'

    HUB_CONTENT_ARN = f"arn:aws:sagemaker:{self.region}:aws:hub-content/SageMakerPublicHub/Model/{model_id}/{model_version}"
    model_name = f"{model_id.upper().replace('-', '_')}_{model_version.replace('.', '_')}"
    endpoint_name = name_from_base(model_id.lower().replace('/', '-').replace('.', '-'))

    endpoint_config = self.node.try_get_context('sagemaker_endpoint_config')
    instance_type = endpoint_config.get('instance_type', 'ml.g6.12xlarge')

    #XXX: Available JumStart Model List
    # https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/src/patterns/gen-ai/aws-model-deployment-sagemaker/jumpstart-model.ts
    self.sagemaker_endpoint = JumpStartSageMakerEndpoint(self, 'JumpStartSageMakerEndpoint',
      model=JumpStartModel.of(model_name),
      accept_eula=True,
      instance_type=SageMakerInstanceType.of(instance_type),
      endpoint_name=endpoint_name
    )
    cdk.Tags.of(self.sagemaker_endpoint).add("sagemaker-studio:hub-content-arn", HUB_CONTENT_ARN)

    cfn_model = self.sagemaker_endpoint.cfn_model

    #XXX: In order to register a SageMaker endpoint with Amazon Bedrock,
    # there must be no unexpected environment variables in your model.
    # The expected environment variables are
    #  SAGEMAKER_PROGRAM,
    #  HF_MODEL_ID,
    #  MODEL_CACHE_ROOT,
    #  SAGEMAKER_ENV,
    #  ENDPOINT_SERVER_TIMEOUT,
    #  NUM_SHARD,
    #  SAGEMAKER_MODEL_SERVER_WORKERS
    cfn_model.add_deletion_override("Properties.PrimaryContainer.Environment.SAGEMAKER_CONTAINER_LOG_LEVEL")
    cfn_model.add_deletion_override("Properties.PrimaryContainer.Environment.SAGEMAKER_MODEL_SERVER_TIMEOUT")

    # The followings are optional
    cfn_model.add_override("Properties.ModelName", endpoint_name)

    cdk.Tags.of(cfn_model).add("sagemaker-sdk:bedrock", "compatible")
    cdk.Tags.of(cfn_model).add("sagemaker-studio:hub-content-arn", HUB_CONTENT_ARN)


    cdk.CfnOutput(self, 'JumpStartModelId',
      value=model_id,
      export_name=f'{self.stack_name}-JumpStartModelId')
    cdk.CfnOutput(self, 'JumpStartModelVersion',
      value=model_version,
      export_name=f'{self.stack_name}-JumpStartModelVersion')
    cdk.CfnOutput(self, 'ModelName',
      value=self.sagemaker_endpoint.cfn_model.attr_model_name,
      export_name=f'{self.stack_name}-ModelName')
    cdk.CfnOutput(self, 'EndpointName',
      value=self.sagemaker_endpoint.cfn_endpoint.endpoint_name,
      export_name=f'{self.stack_name}-EndpointName')
    cdk.CfnOutput(self, 'EndpointArn',
      value=self.sagemaker_endpoint.endpoint_arn,
      export_name=f'{self.stack_name}-EndpointArn')
    cdk.CfnOutput(self, 'HubContentARN',
      value=HUB_CONTENT_ARN,
      export_name=f'{self.stack_name}-HubContentARN')
