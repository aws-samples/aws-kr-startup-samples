#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_sagemaker
)
from constructs import Construct

from cdklabs.generative_ai_cdk_constructs import (
  DeepLearningContainerImage,
)

from .utils import name_from_base


class SageMakerHuggingFaceModelStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, model_id: str, execution_role, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    model_list = self.node.try_get_context('models')
    hf_model_environment = model_list[model_id]

    model_environment = {
      **hf_model_environment
    }

    #XXX: For more information available Amazon Deep Learing Container Images, see:
    # https://github.com/aws/deep-learning-containers/blob/master/available_images.md
    DEFAULT_DLC_IMAGE_URI = {
      'repository_name': 'djl-inference',
      'tag': '0.31.0-lmi13.0.0-cu124'
    }
    dlc_image_uri = self.node.try_get_context('deep_learning_container_image_uri') or DEFAULT_DLC_IMAGE_URI

    #XXX: For api reference, see:
    # https://github.com/awslabs/generative-ai-cdk-constructs/blob/main/src/patterns/gen-ai/aws-model-deployment-sagemaker/deep-learning-container-image.ts
    deeplearning_container_image = DeepLearningContainerImage.from_deep_learning_container_image(
      **dlc_image_uri
    )
    dlc_image = deeplearning_container_image.bind(self, execution_role).image_name;

    model_name = name_from_base(model_id.replace('/', '-').replace('.', '-'))

    self.model = aws_sagemaker.CfnModel(self, "Model",
      execution_role_arn=execution_role.role_arn,
      model_name=model_name,
      primary_container=aws_sagemaker.CfnModel.ContainerDefinitionProperty(
        environment=model_environment,
        #XXX: You need to checkout an available DLC(Deep Learning Container) image in your region.
        # For more information, see https://github.com/aws/deep-learning-containers/blob/master/available_images.md
        image=dlc_image,
      )
    )

    cdk.CfnOutput(self, 'ModelName',
      value=self.model.model_name,
      export_name=f'{self.stack_name}-ModelName')