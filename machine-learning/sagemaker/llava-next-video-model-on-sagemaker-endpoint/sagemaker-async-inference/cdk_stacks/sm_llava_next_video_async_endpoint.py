#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import random
import string

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_iam,
  aws_s3 as s3,
  aws_sns,
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


class LlaVaNeXTVideoAsyncEndpointStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    # Need an existing bucket containing model artifacts that this construct can access
    model_data_source = self.node.try_get_context('model_data_source')

    s3_bucket_name = model_data_source['s3_bucket_name']
    s3_object_key_name = model_data_source['s3_object_key_name']
    assert s3_object_key_name.endswith('.tar.gz') or s3_object_key_name.endswith('/')

    model_data_url = f's3://{s3_bucket_name}/{s3_object_key_name}'

    async_inference_error_sns_topic = aws_sns.Topic(self, 'AsyncInferErrorSNSTopic',
      topic_name='AsyncInferError',
      display_name='Asynchronous Inference Error Topic'
    )

    async_inference_success_sns_topic = aws_sns.Topic(self, 'AsyncInferSuccessSNSTopic',
      topic_name='AsyncInferSuccess',
      display_name='Asynchronous Inference Success Topic'
    )

    S3_DEFAULT_BUCKET_NAME = f'sagemaker-async-inference-{kwargs['env'].region}-{kwargs['env'].account}'
    s3_output_bucket_name = self.node.try_get_context('s3_output_bucket_name') or S3_DEFAULT_BUCKET_NAME
    s3_output_bucket = s3.Bucket(self, "s3bucket",
      bucket_name=s3_output_bucket_name,
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: Default: core.RemovalPolicy.RETAIN - The bucket will be orphaned
      auto_delete_objects=True)

    sagemaker_execution_policy_doc = aws_iam.PolicyDocument()
    sagemaker_execution_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      #XXX: The ARN will be formatted as follows:
      # arn:{partition}:{service}:{region}:{account}:{resource}{sep}{resource-name}
      "resources": [
        self.format_arn(service="sns", region=cdk.Aws.REGION, resource=async_inference_success_sns_topic.topic_name),
        self.format_arn(service="sns", region=cdk.Aws.REGION, resource=async_inference_error_sns_topic.topic_name),
      ],
      "actions": [
        "sns:Publish"
      ]
    }))

    sagemaker_execution_role = aws_iam.Role(self, 'SageMakerEndpointRole',
      role_name=f'AmazonSageMakerEndpointRole-{self.stack_name}',
      assumed_by=aws_iam.ServicePrincipal('sagemaker.amazonaws.com'),
      path='/',
      inline_policies={
        'sagemaker-execution-policy': sagemaker_execution_policy_doc,
      },
      managed_policies=[
        aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSageMakerFullAccess'),
        aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSNSReadOnlyAccess')
      ]
    )

    model_id = self.node.try_get_context('model_id') or 'llava-hf/LLaVA-NeXT-Video-7B-hf'
    sagemaker_endpoint_name = name_from_base(model_id.lower().replace('/', '-').replace('.', '-'))

    dlc_image_info = self.node.try_get_context('dlc_image_info') or {}
    dlc_image_repository_name = dlc_image_info.get('repository_name', 'huggingface-pytorch-inference')
    dlc_image_tag = dlc_image_info.get('tag', '2.3.0-transformers4.46.1-gpu-py311-cu121-ubuntu20.04')

    #XXX: Available Deep Learning Containers (DLC) Images
    # https://github.com/aws/deep-learning-containers/blob/master/available_images.md
    container = DeepLearningContainerImage.from_deep_learning_container_image(
      dlc_image_repository_name,
      dlc_image_tag
    )

    self.sagemaker_endpoint = CustomSageMakerEndpoint(self, 'PyTorchSageMakerEndpoint',
      model_id=model_id,
      instance_type=SageMakerInstanceType.ML_G5_XLARGE,
      container=container,
      model_data_url=model_data_url,
      endpoint_name=sagemaker_endpoint_name,
      role=sagemaker_execution_role,
      environment={
        'HF_MODEL_ID': model_id,

        #XXX: The pipeline tag "video-to-text" is not in the official list.
        # Therefore, set "image-to-text" to task
        'HF_TASK': 'image-to-text',

        #XXX: In order to avoid timeout when torchserver starting.
        'SAGEMAKER_TS_RESPONSE_TIMEOUT': '600'
      },
      # volume_size_in_gb=100
    )

    s3_failure_path = f"s3://{s3_output_bucket.bucket_name}/{sagemaker_endpoint_name}/error"
    s3_output_path = f"s3://{s3_output_bucket.bucket_name}/{sagemaker_endpoint_name}/output"

    async_inference_config = {
      'OutputConfig': {
        'NotificationConfig': {
          'ErrorTopic': async_inference_error_sns_topic.topic_arn,
          'SuccessTopic': async_inference_success_sns_topic.topic_arn
        },
        'S3FailurePath': s3_failure_path,
        'S3OutputPath': s3_output_path
      },
      'ClientConfig': {
        'MaxConcurrentInvocationsPerInstance': 4
      }
    }

    #XXX: For more information, see
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-endpointconfig.html
    self.sagemaker_endpoint.cfn_endpoint_config.add_override(
      'Properties.AsyncInferenceConfig', async_inference_config
    )


    cdk.CfnOutput(self, 'EndpointName',
      value=self.sagemaker_endpoint.cfn_endpoint.endpoint_name,
      export_name=f'{self.stack_name}-EndpointName')
    cdk.CfnOutput(self, 'EndpointArn',
      value=self.sagemaker_endpoint.endpoint_arn,
      export_name=f'{self.stack_name}-EndpointArn')