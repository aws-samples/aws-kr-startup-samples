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
  JumpStartSageMakerEndpoint,
  JumpStartModel,
  SageMakerInstanceType
)

random.seed(47)


def name_from_base(base, max_length=63):
  unique = ''.join(random.sample(string.digits, k=7))
  max_length = 63
  trimmed_base = base[: max_length - len(unique) - 1]
  return "{}-{}".format(trimmed_base, unique)


class SageMakerJumpStartLLMEndpointStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    jumpstart_model = self.node.try_get_context('jumpstart_model_info')
    model_id, model_version = jumpstart_model.get('model_id', 'meta-textgeneration-llama-3-8b-instruct'), jumpstart_model.get('version', '2.0.2')
    model_name = f"{model_id.upper().replace('-', '_')}_{model_version.replace('.', '_')}"

    llm_endpoint_name = name_from_base(model_id.replace('/', '-').replace('.', '-'))

    #XXX: Available JumStart Model List
    # https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/src/patterns/gen-ai/aws-model-deployment-sagemaker/jumpstart-model.ts
    llm_endpoint = JumpStartSageMakerEndpoint(self, 'LLMEndpoint',
      model=JumpStartModel.of(model_name),
      accept_eula=True,
      instance_type=SageMakerInstanceType.ML_G5_12_XLARGE,
      endpoint_name=llm_endpoint_name
    )

    if model_name.startswith('META_TEXTGENERATION_LLAMA_3'):
      #XXX: As of July 2024, Llama3 model artifacts is found only in the private bucket.
      # But `JumpStartSageMakerEndpoint` constructs try to find the model artifact in the public bucket.
      # So it is needed to override the model artifact url as the following:
      jumpstart_model_spec = JumpStartModel.of(model_name).bind()
      artifact_key = jumpstart_model_spec.prepacked_artifact_key if jumpstart_model_spec.prepacked_artifact_key else jumpstart_model_spec.artifact_key
      model_artifact_url = f"s3://jumpstart-private-cache-prod-{kwargs['env'].region}/{artifact_key}"
      llm_endpoint.cfn_model.add_override(
        "Properties.PrimaryContainer.ModelDataSource.S3DataSource.S3Uri",
        model_artifact_url
      )

    cdk.CfnOutput(self, 'LLMEndpointName',
      value=llm_endpoint.cfn_endpoint.endpoint_name,
      export_name=f'{self.stack_name}-LLMEndpointName')
    cdk.CfnOutput(self, 'LLMEndpointArn',
      value=llm_endpoint.endpoint_arn,
      export_name=f'{self.stack_name}-LLMEndpointArn')
