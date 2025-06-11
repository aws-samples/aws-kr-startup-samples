from aws_cdk import (
    Stack,
    aws_sagemaker as sagemaker,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class BgeM3EndpointStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SageMaker execution role
        sagemaker_role = iam.Role(
            self,
            "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
            ],
        )

        # Define model parameters
        model_name = "bge-m3-model"
        endpoint_config_name = "bge-m3-endpoint-config"
        endpoint_name = "bge-m3-endpoint"

        # Define the DJL inference container URI
        region = Stack.of(self).region
        inference_image_uri = f"763104351884.dkr.ecr.{region}.amazonaws.com/djl-inference:0.31.0-lmi13.0.0-cu124"

        # Create SageMaker model
        model = sagemaker.CfnModel(
            self,
            "BgeM3Model",
            execution_role_arn=sagemaker_role.role_arn,
            model_name=model_name,
            primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                image=inference_image_uri,
                # Replace `your-bucket` with your actual S3 bucket name
                # model_data_url="s3://your-bucket/inference_code/BAAI/bge-m3/inference_code.tar.gz",
            ),
        )

        # Create endpoint configuration
        endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            "BgeM3EndpointConfig",
            endpoint_config_name=endpoint_config_name,
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    variant_name="variant1",
                    model_name=model_name,
                    instance_type="ml.g5.xlarge",
                    initial_instance_count=1,
                    container_startup_health_check_timeout_in_seconds=300,
                )
            ],
        )
        endpoint_config.add_dependency(model)

        # Create endpoint
        endpoint = sagemaker.CfnEndpoint(
            self,
            "BgeM3Endpoint",
            endpoint_name=endpoint_name,
            endpoint_config_name=endpoint_config_name,
        )
        endpoint.add_dependency(endpoint_config)

        # Output the endpoint name
        CfnOutput(
            self,
            "EndpointName",
            value=endpoint_name,
        )
