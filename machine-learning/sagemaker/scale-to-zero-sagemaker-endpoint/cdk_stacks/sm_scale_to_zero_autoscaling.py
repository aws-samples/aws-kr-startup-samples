#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Duration,
  Stack,
  aws_applicationautoscaling as aws_appscaling,
  aws_cloudwatch
)
from constructs import Construct


class SageMakerScaleToZeroAutoScalingStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
    sagemaker_inference_component,
    **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    endpoint_config = self.node.try_get_context('sagemaker_endpoint_config')
    managed_instance_scaling = endpoint_config['managed_instance_scaling']
    min_instance_count = managed_instance_scaling['min_instance_count']
    max_instance_count = managed_instance_scaling['max_instance_count']

    inference_component_name = sagemaker_inference_component.inference_component_name

    #XXX: For more information, see
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-applicationautoscaling-scalabletarget.html
    scalable_target = aws_appscaling.ScalableTarget(self, "SageMakerScalableTarget",
      service_namespace=aws_appscaling.ServiceNamespace.SAGEMAKER,
      scalable_dimension="sagemaker:inference-component:DesiredCopyCount",
      min_capacity=min_instance_count,
      max_capacity=max_instance_count,
      resource_id=f"inference-component/{inference_component_name}"
    )

    #XXX: If you want to see an example of autoscaling policy, see
    # https://github.com/aws-samples/sagemaker-genai-hosting-examples/blob/main/scale-to-zero-endpoint/llama3-8b-scale-to-zero-autoscaling.ipynb
    target_tracking_scaling_policy = scalable_target.scale_to_track_metric("SageMakerTargetTrackingScalingPolicy",
      target_value=5, # you need to adjust this value based on your use case
      predefined_metric=aws_appscaling.PredefinedMetric.SAGEMAKER_INFERENCE_COMPONENT_CONCURRENT_REQUESTS_PER_COPY_HIGH_RESOLUTION,
      policy_name=f'Target-tracking-policy-{inference_component_name}',
      scale_in_cooldown=Duration.seconds(300),
      scale_out_cooldown=Duration.seconds(300)
    )

    cloudwatch_metric = aws_cloudwatch.Metric(
      metric_name='NoCapacityInvocationFailures',
      namespace='AWS/SageMaker',
      dimensions_map={
        'InferenceComponentName': inference_component_name
      },
      period=Duration.seconds(10),
      statistic=aws_cloudwatch.Stats.MAXIMUM
    )

    step_scaling_policy = scalable_target.scale_on_metric("SageMakerStepScalingPolicy",
      metric=cloudwatch_metric,
      scaling_steps=[
        aws_appscaling.ScalingInterval(
          upper=0,
          change=0
        ),
        aws_appscaling.ScalingInterval(
          lower=1,
          change=1
        )
      ],
      adjustment_type=aws_appscaling.AdjustmentType.CHANGE_IN_CAPACITY,
      cooldown=Duration.seconds(60),
      datapoints_to_alarm=1,
      evaluation_periods=1,
      metric_aggregation_type=aws_appscaling.MetricAggregationType.MAXIMUM,
    )


    cdk.CfnOutput(self, 'AppScalingTargetId',
      value=scalable_target.scalable_target_id,
      export_name=f'{self.stack_name}-AppScalingTargetId')
    cdk.CfnOutput(self, 'TargetTrackingScalingPolicyArn',
      value=target_tracking_scaling_policy.scaling_policy_arn,
      export_name=f'{self.stack_name}-TargetTrackingScalingPolicyArn')
    cdk.CfnOutput(self, 'StepScalingAlarmName',
      value=step_scaling_policy.upper_alarm.alarm_name,
      export_name=f'{self.stack_name}-StepScalingAlarmName')
