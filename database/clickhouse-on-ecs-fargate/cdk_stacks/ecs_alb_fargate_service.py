#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_ecs_patterns,
)

from constructs import Construct


class ECSAlbFargateServiceStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
    vpc,
    ecs_cluster,
    ecs_task_definition,
    load_balancer,
    sg_efs_inbound,
    cloud_map_service,
    **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    service_name = self.node.try_get_context('ecs_service_name') or "clickhouse"

    self.sg_clickhouse_client = aws_ec2.SecurityGroup(self, 'ClickhouseClientSG',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for clickhouse client',
      security_group_name=f'{self.stack_name.lower()}-clickhouse-client-sg'
    )
    cdk.Tags.of(self.sg_clickhouse_client).add('Name', 'clickhouse-client-sg')

    sg_clickhouse_fargate_service = aws_ec2.SecurityGroup(self, 'ECSFargateServiceSG',
      vpc=vpc,
      allow_all_outbound=True,
      description="Allow inbound from VPC for ECS Fargate Service",
      security_group_name=f'{self.stack_name.lower()}-clickhouse-ecs-service-sg'
    )
    sg_clickhouse_fargate_service.add_ingress_rule(peer=aws_ec2.Peer.ipv4("0.0.0.0/0"),
      connection=aws_ec2.Port.tcp(8123),
      description='clickhouse http interface')
    sg_clickhouse_fargate_service.add_ingress_rule(peer=self.sg_clickhouse_client,
      connection=aws_ec2.Port.tcp(9000),
      description='clickhouse native interface')
    cdk.Tags.of(sg_clickhouse_fargate_service).add('Name', 'clickhouse-ecs-service-sg')

    fargate_service = aws_ecs_patterns.ApplicationLoadBalancedFargateService(self, "ALBFargateService",
      service_name=service_name,
      cluster=ecs_cluster,
      desired_count=1,
      min_healthy_percent=50,
      task_definition=ecs_task_definition,
      load_balancer=load_balancer,
      security_groups=[sg_clickhouse_fargate_service, sg_efs_inbound]
    )
    cdk.Tags.of(fargate_service).add('Name', 'clickhouse')

    fargate_service.service.associate_cloud_map_service(
      service=cloud_map_service,
      container_port=fargate_service.task_definition.default_container.container_port)

    #XXX: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-elasticloadbalancingv2-targetgroup-targetgroupattribute.html
    fargate_service.target_group.set_attribute('deregistration_delay.timeout_seconds', '30')

    self.clickhouse_endpoint = f"clickhouse://{cloud_map_service.service_name}.{cloud_map_service.namespace.namespace_name}:9000"
    self.clickhouse_internal_url = f"http://{cloud_map_service.service_name}.{cloud_map_service.namespace.namespace_name}:8123"
    self.clickhouse_http_endpoint = f'http://{fargate_service.load_balancer.load_balancer_dns_name}'


    cdk.CfnOutput(self, "ClickhouseLocalUrl",
      value=self.clickhouse_internal_url,
      export_name=f'{self.stack_name}-ClickhouseLocalUrl')
    cdk.CfnOutput(self, "ClickhouseEndpoint",
      value=self.clickhouse_endpoint,
      export_name=f'{self.stack_name}-ClickhouseEndpoint')
    cdk.CfnOutput(self, "ClickhouseHTTPEndpoint",
      value=self.clickhouse_http_endpoint,
      export_name=f'{self.stack_name}-ClickhouseHTTPEndpoint')
    cdk.CfnOutput(self, 'ClickhouseClientSecurityGroupId',
      value=self.sg_clickhouse_client.security_group_id,
      export_name=f'{self.stack_name}-ClickhouseClientSecurityGroupId')
    cdk.CfnOutput(self, "ServiceName",
      value=fargate_service.service.service_name,
      export_name=f'{self.stack_name}-ServiceName')
    cdk.CfnOutput(self, "TaskDefinitionArn",
      value=fargate_service.task_definition.task_definition_arn,
      export_name=f'{self.stack_name}-TaskDefinitionArn')
    cdk.CfnOutput(self, "ClusterName",
      value=fargate_service.cluster.cluster_name,
      export_name=f'{self.stack_name}-ClusterName')
