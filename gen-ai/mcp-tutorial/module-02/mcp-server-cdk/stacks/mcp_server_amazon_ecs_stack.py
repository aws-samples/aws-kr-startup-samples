from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    CfnOutput,
    Duration,
)
from constructs import Construct
import os

class McpServerAmazonECSStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC
        vpc_name = "McpServerAmazonECSStackVpc"
        vpc = ec2.Vpc(
            self, "McpServerAmazonECSStackVpc",
            vpc_name=vpc_name,
            max_azs=2,
            nat_gateways=1,
        )

        # Create an ECS cluster
        cluster = ecs.Cluster(
            self, "McpServerAmazonECSStackCluster",
            vpc=vpc,
        )

        # Add EC2 Capacity: Using ARM-based instance (c6g.xlarge)
        cluster.add_capacity("McpServerAmazonECSStackDefaultAutoScalingGroupCapacity",
            instance_type=ec2.InstanceType("c6g.xlarge"),
            desired_capacity=1,
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(ecs.AmiHardwareType.ARM)
        )

        # Create EC2 task definition (Note: EC2 tasks do not support memory and CPU limit parameters)
        task_definition = ecs.Ec2TaskDefinition(
            self,
            "McpServerAmazonECSStackTask"
        )

        # Container definition (Dockerfile must exist in the 'ecs' directory for code deployment)
        container = task_definition.add_container(
            "McpServerAmazonECSStackContainer",
            image=ecs.ContainerImage.from_asset("app"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="McpServerAmazonECSStack"
            ),
            memory_limit_mib=4096,
            cpu=2048
        )

        # Container port mapping
        container.add_port_mappings(
            ecs.PortMapping(container_port=8000)
        )

        # Create EC2-based ECS service (including ALB)
        self.ec2_service = ecs_patterns.ApplicationLoadBalancedEc2Service(
            self, "McpServerAmazonECSStackService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            public_load_balancer=True,
            listener_port=80
        )

        # Configure health check settings
        self.ec2_service.target_group.configure_health_check(
            path="/health",
            healthy_http_codes="200",
            interval=Duration.seconds(5),
            timeout=Duration.seconds(3),
            healthy_threshold_count=2,
            unhealthy_threshold_count=2
        )

        # Configure ALB security group
        self.ec2_service.load_balancer.connections.allow_from_any_ipv4(
            ec2.Port.tcp(80),
            description="Allow inbound HTTP traffic"
        )

        # CloudFormation Outputs: Output ECS service name
        CfnOutput(
            self, "McpServerAmazonECSStackServiceOutput",
            value=self.ec2_service.service.service_name,
            description="The name of the ECS service"
        )

        # CloudFormation Outputs: Output ALB hostname
        CfnOutput(
            self, "McpServerAmazonECSStackALBHostnameOutput",
            value=self.ec2_service.load_balancer.load_balancer_dns_name,
            description="The hostname of the ALB"
        )

        # CloudFormation Outputs: Output ECS Cluster Name
        CfnOutput(
            self, "McpServerAmazonECSStackClusterNameOutput",
            value=cluster.cluster_name,
            description="The name of the ECS Cluster"
        )

        # CloudFormation Outputs: Output ALB Listener ARN
        CfnOutput(
            self, "McpServerAmazonECSStackListenerArnOutput",
            value=self.ec2_service.listener.listener_arn,
            description="The ARN of the Application Load Balancer Listener"
        )

        # CloudFormation Outputs: Output VPC ID
        CfnOutput(
            self, "McpServerAmazonECSStackVpcNameOutput",
            value=vpc.vpc_name,
            description="The name of the VPC"
        )
