from aws_cdk import (
    Stack,
    aws_s3 as s3,
    RemovalPolicy,
)
from constructs import Construct

class S3Bucket(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.s3_base_bucket_name = self.node.try_get_context("s3_base_bucket_name")
        self.s3_base_bucket = s3.Bucket(self, "AmazonBedrockGalleryBaseBucket",
            bucket_name=self.s3_base_bucket_name,
            removal_policy=RemovalPolicy.RETAIN,
        )
        self.s3_base_bucket.add_cors_rule(
            allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
            allowed_origins=["*"],
            allowed_headers=["*"],
            max_age=3000
        )