from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
    aws_lambda as lambda_,
    custom_resources as cr,
    CfnOutput,
    Fn
)
from constructs import Construct

class ChatbotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, knowledge_base_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        knowledge_base_id = Fn.import_value('KnowledgeBaseId')

        # Create ECR image
        image = ecr_assets.DockerImageAsset(self, "ChatbotImage",
            directory="./app",
            platform=ecr_assets.Platform.LINUX_AMD64
        )

        # Create ECS Cluster
        cluster = ecs.Cluster(self, "ChatbotCluster")

        # Create Fargate Service
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "ChatbotService",
            cluster=cluster,
            cpu=256,
            memory_limit_mib=512,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_docker_image_asset(image),
                container_port=8501,  
                environment={
                    "KNOWLEDGE_BASE_ID": knowledge_base_id
                }
            ),
            assign_public_ip=True
        )

        # Add IAM Policy for Amazon Bedrock
        fargate_service.task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:RetrieveAndGenerate",
                    "bedrock:Retrieve"
                ],
                resources=["*"]
            )
        )
        # Create Lambda Function
        start_ingestion_job_lambda = lambda_.Function(
            self, 'StartIngestionJobLambda',
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler='index.handler',
            code=lambda_.Code.from_asset('./lambda/'),
            environment={
                'KNOWLEDGE_BASE_ID': knowledge_base_id
            }
        )

        # Add IAM Policy for Lambda
        start_ingestion_job_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=['bedrock:StartIngestionJob'],
                resources=['*']
            )
        )

        custom_resource_role = iam.Role(
            self, 'CustomResourceRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )

        custom_resource_role.add_to_policy(
            iam.PolicyStatement(
                actions=['lambda:InvokeFunction'],
                resources=[start_ingestion_job_lambda.function_arn]
            )
        )

        # StartIngestionJob Trigger
        cr.AwsCustomResource(
            self, 'TriggerStartIngestionJobLambda',
            on_create=cr.AwsSdkCall(
                service='Lambda',
                action='invoke',
                parameters={
                    'FunctionName': start_ingestion_job_lambda.function_name,
                    'InvocationType': 'Event'
                },
                physical_resource_id=cr.PhysicalResourceId.of('TriggerStartIngestionJobLambda')
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=['lambda:InvokeFunction'],
                    resources=[start_ingestion_job_lambda.function_arn]
                )
            ]),
            role=custom_resource_role
        )

        CfnOutput(self, 'ServiceURL',
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}",
            description='Chatbot Service URL'
        )