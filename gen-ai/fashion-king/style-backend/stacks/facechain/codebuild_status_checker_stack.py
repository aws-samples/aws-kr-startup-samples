from aws_cdk import (
    Stack,
    CustomResource,
    aws_lambda as lambda_,
    aws_iam as iam,
    custom_resources as cr,
    Duration
)
from constructs import Construct

class FaceChainCodeBuildStatusCheckerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, codebuild_projects: list, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a Lambda function to check CodeBuild status
        status_checker_lambda = lambda_.Function(self, "FaceChainCodeBuildStatusChecker",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda/facechain_codebuild_status_checker"),
            timeout=Duration.minutes(15)
        )

        # Grant permissions to the Lambda function
        status_checker_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "codebuild:ListBuildsForProject",
                "codebuild:BatchGetBuilds"
            ],
            resources=["*"]
        ))

        # Create a Custom Resource that uses the Lambda function
        custom_resource = CustomResource(self, "FaceChainCodeBuildStatusResource",
            service_token=cr.Provider(self, "FaceChainCodeBuildStatusProvider",
                on_event_handler=status_checker_lambda
            ).service_token,
            properties={
                "ProjectNames": codebuild_projects
            }
        )

        self.status_resource = custom_resource