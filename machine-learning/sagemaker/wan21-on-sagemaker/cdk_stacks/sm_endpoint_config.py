from aws_cdk import (
    Stack,
    aws_sagemaker as sagemaker,
    CfnOutput
)
from constructs import Construct

class SageMakerEndpointConfigStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, model, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SageMaker endpoint configuration
        self.endpoint_config = sagemaker.CfnEndpointConfig(
            self, "WanVideoEndpointConfig",
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    variant_name="AllTraffic",
                    model_name=model.attr_model_name,
                    instance_type="ml.g6.2xlarge",
                    initial_instance_count=1,
                    initial_variant_weight=1.0
                )
            ]
        )

        # Output value setting
        CfnOutput(
            self, "EndpointConfigName",
            value=self.endpoint_config.attr_endpoint_config_name,
            description="Name of the SageMaker endpoint configuration"
        )