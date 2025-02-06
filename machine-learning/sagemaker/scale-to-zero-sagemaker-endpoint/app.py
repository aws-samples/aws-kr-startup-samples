#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  SageMakerExecutionRoleStack,
  SageMakerHuggingFaceModelStack,
  SageMakerRealtimeEndpointStack,
  SageMakerInferenceComponentStack,
  SageMakerScaleToZeroAutoScalingStack
)


APP_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

sm_execution_role = SageMakerExecutionRoleStack(app, 'SageMakerExecutionRoleStack',
  env=APP_ENV
)

sm_endpoint = SageMakerRealtimeEndpointStack(app, 'SageMakerRealtimeEndpointStack',
  execution_role=sm_execution_role.sagemaker_execution_role,
  env=APP_ENV
)
sm_endpoint.add_dependency(sm_execution_role)

sm_model = SageMakerHuggingFaceModelStack(app, 'SageMakerHuggingFaceModel',
  model_id="deepseek-r1-llama-8b",
  execution_role=sm_execution_role.sagemaker_execution_role,
  env=APP_ENV
)
sm_model.add_dependency(sm_endpoint)

sm_inference_component = SageMakerInferenceComponentStack(app, 'SageMakerInferenceComponent',
  inference_component_name="ic-deepseek-r1-llama-8b",
  model_name=sm_model.model.model_name,
  endpoint_name=sm_endpoint.sagemaker_endpoint.endpoint_name,
  variant_name=sm_endpoint.sagemaker_endpoint_variant_name,
  env=APP_ENV
)
sm_inference_component.add_dependency(sm_model)

sm_scale_to_zero_autoscale = SageMakerScaleToZeroAutoScalingStack(app, 'SageMakerScaleToZeroAutoScalingStack',
  sm_inference_component.sagemaker_inference_component,
  env=APP_ENV
)
sm_scale_to_zero_autoscale.add_dependency(sm_inference_component)

app.synth()