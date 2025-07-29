import aws_cdk as cdk
from aws_cdk import (
    aws_sagemaker as sagemaker,
    Stack,
)

from constructs import Construct

class SageMakerEndpointConfigStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.endpoint_config = sagemaker.CfnEndpointConfig(
            self, "WanVideoRealtimeEndpointConfig",
            production_variants=[sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                initial_instance_count=1,
                initial_variant_weight=1.0,
                instance_type="ml.g6.2xlarge",
                model_name=cdk.Fn.import_value("WanVideoSageMakerModelName"),
                variant_name="AllTraffic"
            )]
        )

        cdk.CfnOutput(
            self, "EndpointConfigName",
            value=self.endpoint_config.attr_endpoint_config_name,
            export_name="WanVideoEndpointConfigName"
        )