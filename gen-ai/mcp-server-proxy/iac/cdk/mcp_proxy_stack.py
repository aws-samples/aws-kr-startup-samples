from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_logs as logs,
    aws_iam as iam,
    CfnOutput,
    Duration
)
from constructs import Construct

class McpProxyStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC 생성
        vpc = ec2.Vpc(
            self, "McpProxyVpc",
            max_azs=2, 
            nat_gateways=1,
        )

        # ECS 클러스터 생성
        cluster_id = "McpProxyCluster"
        cluster = ecs.Cluster(
            self, cluster_id,
            vpc=vpc,
            cluster_name=f"mcp-proxy-cluster-{self.node.addr}"
        )

        # CloudWatch 로그 그룹 생성
        log_group_id = "McpProxyLogGroup"
        log_group = logs.LogGroup(
            self, log_group_id,
            log_group_name=f"/ecs/mcp-proxy-{self.node.addr}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Fargate 서비스 생성
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "McpProxyService",
            cluster=cluster,
            memory_limit_mib=2048,
            cpu=1024,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset("../app"),  # app 디렉토리에서 Docker 이미지 빌드
                container_port=8000,  # 애플리케이션 포트
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="mcp-proxy",
                    log_group=log_group
                ),
                task_role=iam.Role(
                    self, "MCPTaskRole",
                    assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                    role_name=f"mcp-task-role-{self.node.addr}",
                    managed_policies=[
                        iam.ManagedPolicy.from_aws_managed_policy_name("ReadOnlyAccess")
                    ]
                )
            ),
            min_healthy_percent=50,
            public_load_balancer=True,
            service_name="mcp-proxy-service",
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX
            ),
            
        )

        fargate_service.target_group.configure_health_check(
            path="/health"
        )

        CfnOutput(
            self, "ServiceURL",
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}/mcp",
            description="URL of the MCP Proxy service"
        )
