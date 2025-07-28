from aws_cdk import (
    Stack,
    aws_sagemaker as sagemaker,
    CfnOutput
)
from constructs import Construct

class SageMakerEndpointStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, endpoint_config, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SageMaker endpoint
        self.endpoint = sagemaker.CfnEndpoint(
            self, "WanVideoEndpoint",
            endpoint_config_name=endpoint_config.attr_endpoint_config_name,
            endpoint_name="wan-video-endpoint"
        )

        # Output value setting
        CfnOutput(
            self, "EndpointName",
            value=self.endpoint.attr_endpoint_name,
            description="Name of the SageMaker endpoint"
        )