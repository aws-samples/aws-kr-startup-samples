from aws_cdk import (
    Duration,
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_kms as kms,
    aws_secretsmanager as secretsmanager,
    aws_ecr_assets as ecr_assets,
    aws_servicediscovery as sd,
)
from constructs import Construct


class ComputeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        ecs_sg: ec2.SecurityGroup,
        vpclink_sg: ec2.SecurityGroup,
        db_secret: secretsmanager.ISecret,
        kms_key: kms.Key,
        secrets,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        image_asset = ecr_assets.DockerImageAsset(
            self,
            "BackendImage",
            directory="../backend",
            platform=ecr_assets.Platform.LINUX_ARM64,
        )

        execution_role = iam.Role(
            self,
            "ExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )

        task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"],
                resources=[kms_key.key_arn],
            )
        )
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
                conditions={"StringEquals": {"cloudwatch:namespace": "ClaudeCodeProxy"}},
            )
        )
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=["*"],
            )
        )
        db_secret.grant_read(task_role)
        secrets.key_hasher_secret.grant_read(task_role)
        secrets.jwt_secret.grant_read(task_role)
        secrets.admin_credentials.grant_read(task_role)

        private_subnets = ec2.SubnetSelection(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        )

        self.cluster = ecs.Cluster(self, "ProxyCluster", vpc=vpc)

        # Cloud Map namespace for VPC Link service discovery
        namespace = self.cluster.add_default_cloud_map_namespace(
            name="proxy.local", vpc=vpc
        )

        task_def = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            cpu=512,
            memory_limit_mib=1024,
            execution_role=execution_role,
            task_role=task_role,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )

        task_def.add_container(
            "web",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            port_mappings=[ecs.PortMapping(container_port=8000)],
            environment=self._build_environment(kms_key, db_secret, secrets),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="claude-code-proxy"),
        )

        self.service = ecs.FargateService(
            self,
            "ProxyService",
            cluster=self.cluster,
            task_definition=task_def,
            service_name="claude-code-proxy",
            desired_count=2,
            assign_public_ip=False,
            vpc_subnets=private_subnets,
            security_groups=[ecs_sg],
            cloud_map_options=ecs.CloudMapOptions(
                name="backend",
                cloud_map_namespace=namespace,
                dns_record_type=sd.DnsRecordType.SRV,
            ),
            enable_execute_command=True,
        )

        # Expose for API Gateway VPC Link
        self.vpc = vpc
        self.vpclink_sg = vpclink_sg

        CfnOutput(self, "ClusterName", value=self.cluster.cluster_name)
        CfnOutput(self, "ServiceName", value=self.service.service_name)

    def _build_environment(
        self, kms_key: kms.Key, db_secret: secretsmanager.ISecret, secrets,
    ) -> dict[str, str]:
        env = {
            "ENVIRONMENT": self.node.try_get_context("environment") or "dev",
            "LOG_LEVEL": self.node.try_get_context("log_level") or "INFO",
            "PROXY_KMS_KEY_ID": kms_key.key_id,
            "PROXY_DATABASE_URL_ARN": db_secret.secret_arn,
            "PROXY_KEY_HASHER_SECRET_ARN": secrets.key_hasher_secret.secret_arn,
            "PROXY_JWT_SECRET_ARN": secrets.jwt_secret.secret_arn,
            "PROXY_ADMIN_CREDENTIALS_ARN": secrets.admin_credentials.secret_arn,
        }
        if bedrock_region := self.node.try_get_context("bedrock_region"):
            env["PROXY_BEDROCK_REGION"] = bedrock_region
        return env
