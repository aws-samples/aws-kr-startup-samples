from aws_cdk import (
    CfnOutput,
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_ecs_patterns as ecs_patterns,
)
from constructs import Construct

class StreamlitAppStack(Stack):
    def __init__(
            self,
            scope: Construct,
            id: str,
            vpc,
            opensearch_master_user_secret,
            opensearch_domain,
            llm_endpoint,
            embedding_endpoint,
            **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        container_port = self.node.try_get_context("streamlit_container_port") or 8501

        # Create an IAM service role for ECS task execution
        execution_role = iam.Role(
            self, "ECSExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )

        # Create an IAM role for the Fargate task
        task_role = iam.Role(
            self, "ECSTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Role for ECS Tasks to access Secrets Manager and SageMaker"
        )

        # Policy to access Secrets Manager secrets
        secrets_policy = iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[
                opensearch_master_user_secret.secret_arn
            ],
            effect=iam.Effect.ALLOW
        )

        # Policy to invoke SageMaker endpoints
        sagemaker_policy = iam.PolicyStatement(
            actions=["sagemaker:InvokeEndpoint"],
            resources=[
                embedding_endpoint.endpoint_arn,
                llm_endpoint.endpoint_arn
            ],
            effect=iam.Effect.ALLOW
        )

        # Attach policies to the role
        task_role.add_to_policy(secrets_policy)
        task_role.add_to_policy(sagemaker_policy)

        # Set up ECS cluster and networking
        cluster = ecs.Cluster(
            self, "Cluster",
            vpc=vpc
        )

        security_group = ec2.SecurityGroup(
            self, "SecurityGroup",
            vpc=vpc,
            description="Allow traffic on container port",
            allow_all_outbound=True
        )

        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(container_port),
            "Allow inbound traffic"
        )

        # Set up Fargate task definition and service
        task_definition = ecs.FargateTaskDefinition(
            self, "TaskDef",
            memory_limit_mib=512,
            execution_role=execution_role,
            task_role=task_role,
            cpu=256
        )

        container = task_definition.add_container(
            "WebContainer",
            image=ecs.ContainerImage.from_asset("../app/"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="streamlitapp"),
            environment={
                "AWS_REGION": self.region,
                "OPENSEARCH_SECRET": opensearch_master_user_secret.secret_name,
                "OPENSEARCH_DOMAIN_ENDPOINT": f"https://{opensearch_domain.domain_endpoint}",
                "OPENSEARCH_INDEX": "llm_rag_embeddings",
                "EMBEDDING_ENDPOINT_NAME": embedding_endpoint.cfn_endpoint.endpoint_name,
                "TEXT2TEXT_ENDPOINT_NAME": llm_endpoint.cfn_endpoint.endpoint_name
            }
        )
        container.add_port_mappings(ecs.PortMapping(container_port=container_port))

        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "FargateService",
            cluster=cluster,
            task_definition=task_definition,
            public_load_balancer=True,
            assign_public_ip=True
        )


        CfnOutput(self, 'StreamlitEndpoint',
            value=fargate_service.load_balancer.load_balancer_dns_name,
            export_name=f'{self.stack_name}-StreamlitEndpoint'
        )