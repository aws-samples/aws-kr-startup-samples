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


class SageMakerRealtimeEndpointAutoScalingStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, sagemaker_endpoint, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    endpoint_config = self.node.try_get_context('sagemaker_endpoint_config')
    managed_instance_scaling = endpoint_config.get('managed_instance_scaling', {})
    min_instance_count = managed_instance_scaling.get('min_instance_count', 1)
    max_instance_count = managed_instance_scaling.get('max_instance_count', 2)

    endpoint_name = sagemaker_endpoint.cfn_endpoint.endpoint_name
    production_variant_name = sagemaker_endpoint.cfn_endpoint_config.production_variants[0].variant_name

    resource_id = f"endpoint/{endpoint_name}/variant/{production_variant_name}"

    #XXX: For more information, see
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-applicationautoscaling-scalabletarget.html
    scalable_target = aws_appscaling.ScalableTarget(self, "SageMakerVariantScalableTarget",
      service_namespace=aws_appscaling.ServiceNamespace.SAGEMAKER,
      scalable_dimension="sagemaker:variant:DesiredInstanceCount",
      min_capacity=min_instance_count,
      max_capacity=max_instance_count,
      resource_id=resource_id
    )

    approximate_backlog_metric = aws_cloudwatch.Metric(
      metric_name='ApproximateBacklogSizePerInstance',
      namespace='AWS/SageMaker',
      dimensions_map={
        'Endpoint': endpoint_name,
        'Variant': production_variant_name,
      },
      period=Duration.minutes(5),
      statistic=aws_cloudwatch.Stats.AVERAGE
    )

    step_scaling_policy = scalable_target.scale_on_metric("SageMakerStepScalingPolicy",
      metric=approximate_backlog_metric,
      scaling_steps=[
        aws_appscaling.ScalingInterval(
          upper=0,
          lower=0,
          change=-1
        ),
        aws_appscaling.ScalingInterval(
          lower=0.5,
          change=1
        )
      ],
      adjustment_type=aws_appscaling.AdjustmentType.CHANGE_IN_CAPACITY,
      cooldown=Duration.minutes(5),
      datapoints_to_alarm=1,
      evaluation_periods=1
    )


    cdk.CfnOutput(self, 'AppScalingTargetId',
      value=scalable_target.scalable_target_id,
      export_name=f'{self.stack_name}-AppScalingTargetId')
    cdk.CfnOutput(self, 'StepScalingAlarmName',
      value=step_scaling_policy.upper_alarm.alarm_name,
      export_name=f'{self.stack_name}-StepScalingAlarmName')
