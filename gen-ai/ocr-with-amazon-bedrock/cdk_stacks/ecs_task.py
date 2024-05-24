#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,

  aws_ecs,
  aws_iam,
)

from constructs import Construct


class ECSTaskStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    bedrock_access_policy_doc = aws_iam.PolicyDocument()
    bedrock_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "bedrock:ListFoundationModels",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ]
    }))

    task_role = aws_iam.Role(self, "ECSTaskRole",
      role_name=f'ECSTaskRole-{self.stack_name}',
      assumed_by=aws_iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
      inline_policies={
        'bedrock-access-policy': bedrock_access_policy_doc
      },
      managed_policies=[
        aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonECS_FullAccess")
      ]
    )

    task_definition = aws_ecs.FargateTaskDefinition(self, "StreamlitApp",
      task_role=task_role,
      cpu=4 * 1024,
      memory_limit_mib=8 * 1024
    )

    container = task_definition.add_container("Container",
      image=aws_ecs.ContainerImage.from_asset(directory="container",
        asset_name='streamlit-ocr-webapp'),
      logging=aws_ecs.LogDriver.aws_logs(stream_prefix="streamlit-ocr-webapp"),
    )
    port_mapping = aws_ecs.PortMapping(
      container_port=8501,
      host_port=8501,
      protocol=aws_ecs.Protocol.TCP
    )
    container.add_port_mappings(port_mapping)

    self.ecs_task_definition = task_definition

    cdk.CfnOutput(self, 'TaskDefinitionArn',
      value=self.ecs_task_definition.task_definition_arn,
      export_name=f'{self.stack_name}-TaskDefinitionArn')
