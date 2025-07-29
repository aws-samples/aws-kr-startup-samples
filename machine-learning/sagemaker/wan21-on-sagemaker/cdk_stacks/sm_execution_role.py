from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct

class SageMakerExecutionRoleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 bucket for Async Inference output
        self.s3_output_bucket = s3.Bucket(
            self, "AsyncOutputBucket",
            bucket_name=f"sagemaker-async-output-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY, # For demo purposes
            auto_delete_objects=True # For demo purposes
        )

        # Create SageMaker execution role
        self.sm_execution_role = iam.Role(
            self, "WanVideoExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess") # Simplified for demo
            ]
        )

        # Add specific policy to allow writing to the output bucket
        self.sm_execution_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
            resources=[
                self.s3_output_bucket.bucket_arn,
                f"{self.s3_output_bucket.bucket_arn}/*"
            ]
        ))

        # Output value setting
        CfnOutput(
            self, "SageMakerExecutionRoleArn",
            value=self.sm_execution_role.role_arn,
            description="ARN of the SageMaker execution role"
        )
        CfnOutput(
            self, "AsyncOutputBucketName",
            value=self.s3_output_bucket.bucket_name,
            description="Name of the S3 bucket for async inference output"
        )