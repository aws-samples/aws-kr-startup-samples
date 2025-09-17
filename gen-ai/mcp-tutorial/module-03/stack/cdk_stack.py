from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    CfnOutput,
    Duration,
)
from constructs import Construct

class McpServerAmazonECSStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc_id = self.node.try_get_context("vpc-id")
        cluster_name = self.node.try_get_context("cluster-name")
        listener_arn = self.node.try_get_context("listener-arn")

        # Reference the existing VPC
        vpc = ec2.Vpc.from_lookup(self, "ExistingVPC",
                                  is_default=False,
                                  vpc_id=vpc_id
                                  )
        
        # Reference the existing ECS cluster
        cluster = ecs.Cluster.from_cluster_attributes(
            self, "McpServerAmazonECSStackCluster",
            cluster_name=cluster_name,
            vpc=vpc,
            security_groups=[]
        )

        # Create EC2 task definition
        task_definition = ecs.Ec2TaskDefinition(
            self,
            "StreamlitAppTask"
        )

        # Add Bedrock invoke permissions to the task role
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=["*"]
            )
        )

        # Container definition
        container = task_definition.add_container(
            "StreamlitAppContainer",
            image=ecs.ContainerImage.from_asset("app"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="StreamlitApp"
            ),
            memory_limit_mib=2048,
            cpu=1024
        )

        # Container port mapping for Streamlit
        container.add_port_mappings(
            ecs.PortMapping(container_port=8501)
        )

        # Reference existing load balancer and listener
        listener = elbv2.ApplicationListener.from_lookup(
            self, "ExistingListener", 
            listener_arn=listener_arn
        )

        # Create a target group for the Streamlit app
        target_group = elbv2.ApplicationTargetGroup(
            self, "StreamlitAppTargetGroup",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            health_check=elbv2.HealthCheck(
                path="/",
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3
            )
        )

        # Add a rule to the listener to route traffic to the target group with path rewrite
        listener.add_action(
            "StreamlitAppRule",
            priority=10,
            conditions=[
                elbv2.ListenerCondition.path_patterns(["/app", "/app/*", "/_stcore/*", "/static/*"])
            ],
            action=elbv2.ListenerAction.forward(
                target_groups=[target_group],
            )
        )

        # Create ECS service with load balancer integration
        service = ecs.Ec2Service(
            self, "StreamlitAppService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            cloud_map_options=None
        )
        
        # Associate ECS service with target group
        service.attach_to_application_target_group(target_group)

        # CloudFormation Outputs: Output ECS service name
        CfnOutput(
            self, "StreamlitAppServiceOutput",
            value=service.service_name,
            description="The name of the Streamlit ECS service"
        )
