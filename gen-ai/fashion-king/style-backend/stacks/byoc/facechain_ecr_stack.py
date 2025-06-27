from aws_cdk import CfnOutput, Stack, RemovalPolicy
from aws_cdk import aws_ecr as ecr
from constructs import Construct

class ByocFaceChainEcrStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create an ECR repository
        self.repository = ecr.Repository(self, "ByocFacechainRepository", 
                                         repository_name="byoc-facechain-repo",
                                         removal_policy=RemovalPolicy.RETAIN)
        
        # Outputs
        CfnOutput(self, "ByocFacechainRepositoryUri", value=self.repository.repository_uri, description="The URI of the BYOC Facechain ECR repository")

        CfnOutput(self, "ByocFacechainRepositoryName", value=self.repository.repository_name, description="The name of the BYOC Facechain ECR repository")
