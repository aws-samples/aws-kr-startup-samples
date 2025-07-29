import aws_cdk as cdk
from aws_cdk import (
    aws_sagemaker as sagemaker,
    Stack,
)
from constructs import Construct

class SageMakerEndpointConfigStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, model, s3_output_bucket, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SageMaker Endpoint Configuration
        self.endpoint_config = sagemaker.CfnEndpointConfig(
            self, "WanVideoRealtimeEndpointConfig", # Changed resource name
            production_variants=[sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                initial_instance_count=1,
                initial_variant_weight=1.0,
                instance_type="ml.g6.2xlarge",  # Changed to requested type
                model_name=model.attr_model_name,  # 원래처럼 직접 사용
                variant_name="AllTraffic"
            )]
        )

        # Export Endpoint Configuration name
        cdk.CfnOutput(
            self, "EndpointConfigName",
            value=self.endpoint_config.attr_endpoint_config_name,
            export_name="WanVideoEndpointConfigName"
        )