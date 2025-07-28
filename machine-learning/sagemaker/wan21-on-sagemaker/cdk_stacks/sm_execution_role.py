from aws_cdk import (
    Stack,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct

class SageMakerExecutionRoleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SageMaker execution role
        self.sm_execution_role = iam.Role(
            self, "WanVideoSageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonElasticContainerRegistryPublicFullAccess")
            ]
        )

        # Add S3 bucket access permissions
        self.sm_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                resources=["*"]
            )
        )

        # Add CloudWatch Logs permissions
        self.sm_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=["*"]
            )
        )

        # Output value setting
        CfnOutput(
            self, "SageMakerExecutionRoleArn",
            value=self.sm_execution_role.role_arn,
            description="ARN of the SageMaker execution role"
        )