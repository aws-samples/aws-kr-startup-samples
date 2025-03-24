import os
from aws_cdk import (
    App,
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_logs as logs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
)
from aws_cdk.aws_ecr_assets import DockerImageAsset
from constructs import Construct

class TranslatorFargateStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        docker_image_asset = DockerImageAsset(
            self, "TranslatorDockerImage",
            directory="../app/",
        )

        vpc = ec2.Vpc(
            self, "TranslatorVpc",
            max_azs=2,
            nat_gateways=1,
        )

        cluster = ecs.Cluster(
            self, "TranslatorCluster",
            vpc=vpc,
            container_insights=True,
        )

        alb_sg = ec2.SecurityGroup(
            self, "AlbSecurityGroup",
            vpc=vpc,
            description="Security group for ALB",
            allow_all_outbound=True,
        )

        task_definition = ecs.FargateTaskDefinition(
            self, "TranslatorTaskDef",
            memory_limit_mib=1024,
            cpu=256,
        )

        log_group = logs.LogGroup(
            self, "TranslatorLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        container = task_definition.add_container(
            "TranslatorContainer",
            image=ecs.ContainerImage.from_docker_image_asset(docker_image_asset),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="translator",
                log_group=log_group,
            ),
        )
        
        container.add_port_mappings(
            ecs.PortMapping(container_port=8501)
        )
        
        service_sg = ec2.SecurityGroup(
            self, "ServiceSecurityGroup",
            vpc=vpc,
            description="Security group for Fargate Service",
            allow_all_outbound=True,
        )

        service_sg.add_ingress_rule(
            peer=alb_sg,
            connection=ec2.Port.tcp(8501),
            description="Allow traffic from ALB to container"
        )
        
        service = ecs.FargateService(
            self, "TranslatorService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            security_groups=[service_sg],
            assign_public_ip=False,
            health_check_grace_period=Duration.seconds(120),
            min_healthy_percent=100,
        )
        
        lb = elbv2.ApplicationLoadBalancer(
            self, "TranslatorALB",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg,
        )
        
        target_group = elbv2.ApplicationTargetGroup(
            self, "TranslatorTargetGroup",
            vpc=vpc,
            port=8501,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/",
                healthy_http_codes="200",
                interval=Duration.seconds(60),
                timeout=Duration.seconds(30),
            )
        )
        
        target_group.add_target(service)
        
        listener = lb.add_listener(
            "HttpListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_target_groups=[target_group],
        )
        
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:*"],
                resources=["*"],
            )
        )

        CfnOutput(
            self, "LoadBalancerDNS",
            value=lb.load_balancer_dns_name,
            description="Loadbalancer URL",
        )
        
        CfnOutput(
            self, "DockerImageUri",
            value=docker_image_asset.image_uri,
            description="docker image URI",
        )

app = App()
TranslatorFargateStack(app, "TranslatorFargateStack")
app.synth()