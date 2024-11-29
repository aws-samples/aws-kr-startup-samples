from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    CfnOutput,
    Duration
)
from constructs import Construct

class PersonaChatbotUsermadeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(
            self, "ChatbotVpc",
            max_azs=2,
            nat_gateways=1
        )

        cluster = ecs.Cluster(
            self, "ChatbotCluster",
            vpc=vpc,
            container_insights=True
        )

        # IAM role for Bedrock access
        task_role = iam.Role(
            self, "ChatbotTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )
        
        task_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:*"],
            resources=["*"]
        ))

        task_definition = ecs.FargateTaskDefinition(
            self, "ChatbotTask",
            memory_limit_mib=2048,
            cpu=1024,
            task_role=task_role
        )

        container = task_definition.add_container(
            "ChatbotContainer",
            image=ecs.ContainerImage.from_asset("./app"),
            port_mappings=[ecs.PortMapping(container_port=8501)],
            environment={
                "AWS_DEFAULT_REGION": Stack.of(self).region
            },
            logging=ecs.LogDrivers.aws_logs(stream_prefix="chatbot")
        )

        alb = elbv2.ApplicationLoadBalancer(
            self, "ChatbotALB",
            vpc=vpc,
            internet_facing=True
        )

        listener = alb.add_listener(
            "ChatbotListener",
            port=80
        )

        service = ecs.FargateService(
            self, "ChatbotService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=2,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )

        listener.add_targets(
            "ChatbotTarget",
            port=8501,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service],
            health_check=elbv2.HealthCheck(
                path="/_stcore/health",
                interval=Duration.seconds(30)
            )
        )

        CfnOutput(
            self, "AlbDnsName",
            value=alb.load_balancer_dns_name,
            description="ALB DNS Name"
        )