from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
    Duration,
)
from constructs import Construct
import os

class McpServerCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(
            self, "McpServerVpc",
            max_azs=2,
            nat_gateways=1,
        )

        # Create an ECS cluster
        cluster = ecs.Cluster(
            self, "McpServerCluster",
            vpc=vpc,
        )

        # Build Docker image from local directory
        app_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app")
        asset = ecr_assets.DockerImageAsset(
            self, "McpServerImage",
            directory=app_directory,
        )

        # Create a Fargate task definition
        task_definition = ecs.FargateTaskDefinition(
            self, "McpServerTaskDef",
            memory_limit_mib=512,
            cpu=256,
        )

        # Add container to the task definition
        container = task_definition.add_container(
            "McpServerContainer",
            image=ecs.ContainerImage.from_docker_image_asset(asset),
            logging=ecs.AwsLogDriver(
                stream_prefix="mcp-server"
            ),
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60),
            ),
        )

        # Add port mapping to the container
        container.add_port_mappings(
            ecs.PortMapping(
                container_port=8000,
                host_port=8000,
                protocol=ecs.Protocol.TCP
            )
        )

        # Create a Fargate service
        service = ecs.FargateService(
            self, "McpServerService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=2,
            assign_public_ip=True,
            security_groups=[
                ec2.SecurityGroup(
                    self, "McpServerSG",
                    vpc=vpc,
                    allow_all_outbound=True,
                )
            ],
        )

        # Create an Application Load Balancer
        lb = elbv2.ApplicationLoadBalancer(
            self, "McpServerLB",
            vpc=vpc,
            internet_facing=True,
        )

        # Add a listener to the load balancer
        listener = lb.add_listener(
            "McpServerListener",
            port=80,
        )

        # Add the service as a target to the listener
        listener.add_targets(
            "McpServerTarget",
            port=80,
            targets=[service],
            health_check=elbv2.HealthCheck(
                path="/health",
                port="8000",
                interval=Duration.seconds(60),
                timeout=Duration.seconds(5),
            ),
        )

        # Allow the load balancer to access the service
        service.connections.allow_from(
            lb, 
            ec2.Port.tcp(8000),
            "Allow traffic from ALB to Fargate service"
        )

        # Output the load balancer DNS name
        CfnOutput(
            self, "LoadBalancerDNS",
            value=lb.load_balancer_dns_name,
            description="The DNS name of the load balancer"
        )
