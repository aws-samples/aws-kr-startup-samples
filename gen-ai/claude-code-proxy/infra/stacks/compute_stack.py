from aws_cdk import (
    Duration,
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_kms as kms,
    aws_secretsmanager as secretsmanager,
    aws_ecr_assets as ecr_assets,
)
from constructs import Construct


class ComputeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        alb_sg: ec2.SecurityGroup,
        ecs_sg: ec2.SecurityGroup,
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

        # Execution role lets ECS pull the image and publish logs.
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

        # Task role needs KMS, metrics, and Bedrock permissions at runtime.
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
        # Secrets read access is required for runtime config values.
        db_secret.grant_read(task_role)
        secrets.key_hasher_secret.grant_read(task_role)
        secrets.jwt_secret.grant_read(task_role)
        secrets.admin_credentials.grant_read(task_role)

        private_subnets = ec2.SubnetSelection(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        )

        cluster = ecs.Cluster(self, "ProxyCluster", vpc=vpc)

        load_balancer = elbv2.ApplicationLoadBalancer(
            self,
            "ProxyAlb",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            idle_timeout=Duration.seconds(300),
        )

        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "ProxyService",
            cluster=cluster,
            service_name="claude-code-proxy",
            load_balancer=load_balancer,
            public_load_balancer=True,
            open_listener=False,
            desired_count=2,
            assign_public_ip=False,
            cpu=512,
            memory_limit_mib=1024,
            task_subnets=private_subnets,
            security_groups=[ecs_sg],
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_docker_image_asset(image_asset),
                container_port=8000,
                environment=self._build_environment(kms_key, db_secret, secrets),
                execution_role=execution_role,
                task_role=task_role,
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="claude-code-proxy"
                ),
            ),
            enable_execute_command=True,
        )

        fargate_service.target_group.configure_health_check(path="/health")

        self.service_name = fargate_service.service.service_name
        self.service_arn = fargate_service.service.service_arn

        self.load_balancer = fargate_service.load_balancer

        self.backend_url = f"http://{fargate_service.load_balancer.load_balancer_dns_name}"

        # Shared secret restricts ALB access to CloudFront traffic.
        self.origin_verify_secret = secretsmanager.Secret(
            self,
            "OriginVerifySecret",
            secret_name="cloudfront-origin-verify-secret",
            description="Secret header value for CloudFront to ALB verification",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                password_length=32,
            ),
        )

        listener = fargate_service.listener

        # Require X-Origin-Verify header; default action denies direct ALB access.
        elbv2.ApplicationListenerRule(
            self,
            "ValidOriginRule",
            listener=listener,
            priority=1,
            conditions=[
                elbv2.ListenerCondition.http_header(
                    "X-Origin-Verify",
                    [self.origin_verify_secret.secret_value.unsafe_unwrap()],
                ),
            ],
            target_groups=[fargate_service.target_group],
        )

        cfn_listener = listener.node.default_child
        cfn_listener.add_property_override(
            "DefaultActions",
            [
                {
                    "Type": "fixed-response",
                    "FixedResponseConfig": {
                        "StatusCode": "403",
                        "ContentType": "text/plain",
                        "MessageBody": "Access Denied",
                    },
                }
            ],
        )

        CfnOutput(
            self,
            "OriginVerifySecretArn",
            value=self.origin_verify_secret.secret_arn,
            description="Origin Verify Secret ARN for CloudFront configuration",
        )

    def _build_environment(
        self,
        kms_key: kms.Key,
        db_secret: secretsmanager.ISecret,
        secrets,
    ) -> dict[str, str]:
        """Build environment variables for the ECS task.

        Supports CDK context variables for optional configuration:
            - environment: Deployment environment (default: "dev")
            - log_level: Log level (default: "INFO")
            - plan_force_rate_limit: Force rate limiting on Plan API (default: "false")
            - plan_api_key: Anthropic API key (optional)
            - bedrock_region: Bedrock region (optional)
            - bedrock_default_model: Default Bedrock model (optional)
            - cors_allowed_origins: JSON list string for CORS allowlist
            - cors_allowed_methods: JSON list string for CORS methods
            - cors_allowed_headers: JSON list string for CORS headers
            - cors_allow_credentials: "true" or "false"

        Usage:
            cdk deploy --context environment=prod --context log_level=DEBUG
        """
        env = {
            "ENVIRONMENT": self.node.try_get_context("environment") or "dev",
            "LOG_LEVEL": self.node.try_get_context("log_level") or "INFO",
            "PROXY_KMS_KEY_ID": kms_key.key_id,
            "PROXY_DATABASE_URL_ARN": db_secret.secret_arn,
            "PROXY_KEY_HASHER_SECRET_ARN": secrets.key_hasher_secret.secret_arn,
            "PROXY_JWT_SECRET_ARN": secrets.jwt_secret.secret_arn,
            "PROXY_ADMIN_CREDENTIALS_ARN": secrets.admin_credentials.secret_arn,
        }

        # Optional context-based environment variables
        if plan_api_key := self.node.try_get_context("plan_api_key"):
            env["PROXY_PLAN_API_KEY"] = plan_api_key

        if bedrock_region := self.node.try_get_context("bedrock_region"):
            env["PROXY_BEDROCK_REGION"] = bedrock_region

        if bedrock_default_model := self.node.try_get_context("bedrock_default_model"):
            env["PROXY_BEDROCK_DEFAULT_MODEL"] = bedrock_default_model

        if cors_allowed_origins := self.node.try_get_context("cors_allowed_origins"):
            env["PROXY_CORS_ALLOWED_ORIGINS"] = cors_allowed_origins

        if cors_allowed_methods := self.node.try_get_context("cors_allowed_methods"):
            env["PROXY_CORS_ALLOWED_METHODS"] = cors_allowed_methods

        if cors_allowed_headers := self.node.try_get_context("cors_allowed_headers"):
            env["PROXY_CORS_ALLOWED_HEADERS"] = cors_allowed_headers

        if cors_allow_credentials := self.node.try_get_context("cors_allow_credentials"):
            env["PROXY_CORS_ALLOW_CREDENTIALS"] = cors_allow_credentials

        return env
