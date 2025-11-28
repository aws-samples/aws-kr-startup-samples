from aws_cdk import (
    Stack,
    Duration,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
    aws_ecr_assets as ecr_assets,
    RemovalPolicy,
)
from constructs import Construct


class ClaudeProxyFargateStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(
            self,
            "ClaudeProxyVpc",
            max_azs=2,
            nat_gateways=0,
        )

        cluster = ecs.Cluster(
            self,
            "ClaudeProxyCluster",
            vpc=vpc,
            container_insights=True,
        )

        rate_limit_table = dynamodb.Table(
            self,
            "RateLimitTable",
            table_name="claude-proxy-rate-limits",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.RETAIN,
        )

        usage_table = dynamodb.Table(
            self,
            "UsageTable",
            table_name="claude-proxy-usage",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.RETAIN,
        )

        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "ClaudeProxyService",
            cluster=cluster,
            cpu=512,
            memory_limit_mib=1024,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    "../app",
                    platform=ecr_assets.Platform.LINUX_AMD64,
                ),
                container_port=8080,
                environment={
                    "BEDROCK_FALLBACK_ENABLED": "true",
                    "RATE_LIMIT_TRACKING_ENABLED": "true",
                    "RATE_LIMIT_TABLE_NAME": rate_limit_table.table_name,
                    "USAGE_TRACKING_ENABLED": "true",
                    "USAGE_TABLE_NAME": usage_table.table_name,
                    "AWS_DEFAULT_REGION": self.region,
                },
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="claude-proxy",
                    log_retention=logs.RetentionDays.ONE_WEEK,
                ),
            ),
            public_load_balancer=True,
            assign_public_ip=True,
            health_check_grace_period=Duration.seconds(60),
        )

        fargate_service.target_group.configure_health_check(
            path="/health",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
        )

        rate_limit_table.grant_read_write_data(
            fargate_service.task_definition.task_role
        )
        usage_table.grant_read_write_data(fargate_service.task_definition.task_role)

        fargate_service.task_definition.task_role.add_to_principal_policy(
            statement=self._create_bedrock_policy()
        )

        from aws_cdk import CfnOutput

        CfnOutput(
            self,
            "LoadBalancerDNS",
            value=fargate_service.load_balancer.load_balancer_dns_name,
            description="ALB DNS Name",
        )

        CfnOutput(
            self,
            "ServiceURL",
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}",
            description="Service URL",
        )

    def _create_bedrock_policy(self):
        from aws_cdk import aws_iam as iam

        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
            ],
            resources=["*"],
        )
