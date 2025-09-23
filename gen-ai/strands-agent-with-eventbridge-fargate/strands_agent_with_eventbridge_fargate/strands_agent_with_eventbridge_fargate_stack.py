from aws_cdk import (
    Duration,
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_s3 as s3,
    aws_logs as logs,
    aws_events as events,
    aws_events_targets as targets,
    aws_ecr_assets as ecr_assets,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
import os


class StrandsAgentWithEventbridgeFargateStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC 생성
        vpc = ec2.Vpc(
            self, "StrandsAgentVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # S3 버킷 생성
        data_bucket = s3.Bucket(
            self, "StrandsAgentDataBucket",
            bucket_name=f"strands-agent-eventbridge-{self.account}-{self.region}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # CloudWatch 로그 그룹
        log_group = logs.LogGroup(
            self, "StrandsAgentLogGroup",
            log_group_name="/aws/ecs/strands-agent",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        # ECS 클러스터
        cluster = ecs.Cluster(
            self, "StrandsAgentCluster",
            vpc=vpc,
            cluster_name="strands-agent-cluster"
        )

        # Docker 이미지 빌드 및 ECR 푸시
        docker_image = ecr_assets.DockerImageAsset(
            self, "StrandsAgentImage",
            directory=os.path.join(os.path.dirname(__file__), "..", "docker"),
            platform=ecr_assets.Platform.LINUX_ARM64
        )

        # 태스크 실행 역할
        task_execution_role = iam.Role(
            self, "TaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )

        # 태스크 역할
        task_role = iam.Role(
            self, "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )

        # S3 접근 권한
        data_bucket.grant_read_write(task_role)

        # Bedrock 접근 권한
        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )

        # 보안 그룹
        security_group = ec2.SecurityGroup(
            self, "StrandsAgentSecurityGroup",
            vpc=vpc,
            description="Security group for Strands Agent ECS tasks",
            allow_all_outbound=True
        )

        # ECS 태스크 정의
        task_definition = ecs.FargateTaskDefinition(
            self, "StrandsAgentTaskDefinition",
            memory_limit_mib=2048,
            cpu=512,
            execution_role=task_execution_role,
            task_role=task_role,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX
            )
        )

        # 컨테이너 추가
        task_definition.add_container(
            "StrandsAgentContainer",
            image=ecs.ContainerImage.from_docker_image_asset(docker_image),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="strands-agent",
                log_group=log_group
            ),
            environment={
                "S3_BUCKET": data_bucket.bucket_name,
                "AWS_DEFAULT_REGION": self.region
            }
        )

        # EventBridge 실행 역할
        eventbridge_role = iam.Role(
            self, "EventBridgeExecutionRole",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
            inline_policies={
                "ECSRunTaskPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["ecs:RunTask"],
                            resources=[task_definition.task_definition_arn]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["iam:PassRole"],
                            resources=[
                                task_execution_role.role_arn,
                                task_role.role_arn
                            ]
                        )
                    ]
                )
            }
        )

        # EventBridge 규칙 (30분마다)
        schedule_rule = events.Rule(
            self, "StrandsAgentScheduleRule",
            description="Schedule rule for Strands Agent (every 30 minutes)",
            schedule=events.Schedule.rate(Duration.minutes(30))
        )

        # EventBridge 타겟
        schedule_rule.add_target(
            targets.EcsTask(
                cluster=cluster,
                task_definition=task_definition,
                subnet_selection=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
                security_groups=[security_group],
                role=eventbridge_role,
                platform_version=ecs.FargatePlatformVersion.LATEST
            )
        )

        # 출력
        CfnOutput(self, "VpcId", value=vpc.vpc_id)
        CfnOutput(self, "ClusterArn", value=cluster.cluster_arn)
        CfnOutput(self, "TaskDefinitionArn", value=task_definition.task_definition_arn)
        CfnOutput(self, "S3BucketName", value=data_bucket.bucket_name)
        CfnOutput(self, "DockerImageUri", value=docker_image.image_uri)
