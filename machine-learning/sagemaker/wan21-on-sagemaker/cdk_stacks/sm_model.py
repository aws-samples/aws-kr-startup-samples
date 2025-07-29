from aws_cdk import (
    Stack,
    aws_sagemaker as sagemaker,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_ecr_assets as ecr_assets,
    CfnOutput,
    RemovalPolicy,
    aws_s3_assets as s3_assets
)
from constructs import Construct
import os

class SageMakerWanModelStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, execution_role, model_data_url=None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Build Docker image and push to ECR
        docker_image = ecr_assets.DockerImageAsset(
            self, "WanVideoDockerImage",
            directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "inference_code")
        )

        self.model = sagemaker.CfnModel(
            self, "WanVideoModel",
            execution_role_arn=execution_role.role_arn,
            primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                image=docker_image.image_uri,
                model_data_url=f"s3://{os.environ.get('S3_BUCKET_NAME', 'wan-model-bucket-default')}/models/wan2.1-t2v-1.3b/model.tar.gz",
                environment={
                    "PRELOAD_TASK": "t2v-1.3B",
                    "S3_BUCKET_NAME": os.environ.get('S3_BUCKET_NAME', 'wan-model-bucket-default'),
                    "MODEL_S3_KEY": "models/wan2.1-t2v-1.3b/",
                    "DOWNLOAD_FROM_HF": "false",
                    "SAGEMAKER_CONTAINER_LOG_LEVEL": "20",
                    "SAGEMAKER_REGION": self.region,
                    "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"
                }
            )
        )