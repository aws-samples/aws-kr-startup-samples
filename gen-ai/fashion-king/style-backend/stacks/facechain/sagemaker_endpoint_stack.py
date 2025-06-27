from aws_cdk import Stack, CustomResource
from aws_cdk import aws_sagemaker as sagemaker
from aws_cdk import aws_iam as iam
from constructs import Construct

class FaceChainSageMakerEndpointStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, facechain_image_uri: str, codebuild_status_resource: CustomResource, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        facechain_sagemaker_endpoint_name = self.node.try_get_context("facechain_sagemaker_endpoint_name")
        facechain_sagemaker_endpoint_instance_count = self.node.try_get_context("facechain_sagemaker_endpoint_instance_count")
        facechain_sagemaker_endpoint_instance_type = self.node.try_get_context("facechain_sagemaker_endpoint_instance_type")

        # Add a dependency on the CodeBuild status resource
        self.node.add_dependency(codebuild_status_resource)
        
        # Create IAM Role for SageMaker
        sagemaker_role = iam.Role(self, "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
            ]
        )

        # Create SageMaker Model for FaceChain
        facechain_model = sagemaker.CfnModel(self, "FaceChainSageMakerModel",
            execution_role_arn=sagemaker_role.role_arn,
            primary_container={
                "image": facechain_image_uri,
                "mode": "SingleModel"
            },
            model_name="facechain-sagemaker-model"
        )

        # Create SageMaker Endpoint Configuration for FaceChain
        facechain_endpoint_config = sagemaker.CfnEndpointConfig(self, "FaceChainSageMakerEndpointConfig",
            production_variants=[
                {
                    "initialInstanceCount": facechain_sagemaker_endpoint_instance_count,
                    "instanceType": facechain_sagemaker_endpoint_instance_type,
                    "modelName": facechain_model.model_name,
                    "variantName": "FaceChainVariant",
                    "initialVariantWeight": 1
                }
            ],
            endpoint_config_name="facechain-sagemaker-endpoint-config"
        )
        facechain_endpoint_config.add_dependency(facechain_model)

        # Create SageMaker Endpoint for FaceChain
        facechain_endpoint = sagemaker.CfnEndpoint(self, "FaceChainSageMakerEndpoint",
            endpoint_config_name=facechain_endpoint_config.endpoint_config_name,
            endpoint_name=facechain_sagemaker_endpoint_name
        )
        facechain_endpoint.add_dependency(facechain_endpoint_config)

        # Store the endpoint name as an instance variable
        self.facechain_endpoint_name = facechain_endpoint.endpoint_name