import os
import subprocess

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from aws_cdk.aws_s3 import Bucket, CorsRule, HttpMethods
from aws_cdk.aws_lambda import Function, Code, LayerVersion, Runtime
from aws_cdk.aws_apigateway import RestApi, LambdaIntegration, AuthorizationType, MethodResponse
from aws_cdk.aws_iam import PolicyStatement, Effect
from aws_cdk.aws_dynamodb import Table, Attribute, AttributeType, BillingMode
from constructs import Construct


class VideoMakerWithNovaReelStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context information
        self.video_generation_model_id = self.node.try_get_context("video_generation_model_id")
        self.s3_base_bucket_name = self.node.try_get_context("s3_base_bucket_name")
        self.s3_stack_bucket_name = f"{self.s3_base_bucket_name}-{self.node.id}".lower()
        self.ddb_table_name = self.node.try_get_context("video_maker_with_nova_reel_process_table")

        # Create DynamoDB table
        self.video_maker_with_nova_reel_process_table = Table(
            self, "VideoMakerWithNovaReelProcessTable",
            table_name=self.ddb_table_name,
            partition_key=Attribute(
                name="invocation_id",
                type=AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=BillingMode.PAY_PER_REQUEST,
        )

        # Create S3 bucket with CORS configuration
        self.s3_base_bucket = self._create_s3_bucket(self.s3_stack_bucket_name)

        # Output S3 bucket name (CFN Output)
        CfnOutput(
            self, "VideoMakerWithNovaReelS3Bucket",
            value=self.s3_base_bucket.bucket_name,
            description="The name of the S3 bucket used by the VideoMakerWithNovaReel application"
        )

        # Create API Gateway and resources
        self.api_gateway = self._create_api_gateway()
        self._create_api_resources()

        # Create Lambda layer (dependencies)
        dependencies_layer = self._create_dependencies_layer()

        # Create video generation Lambda function
        self.lambda_func = self._create_video_lambda(
            model_id=self.video_generation_model_id,
            bucket_name=self.s3_stack_bucket_name,
            layer=dependencies_layer
        )

        # Add dependency to ensure Lambda function is created after S3 bucket
        self.lambda_func.node.add_dependency(self.s3_base_bucket)

        # Grant S3 and AWS Bedrock permissions to Lambda function
        self._attach_lambda_permissions(self.s3_stack_bucket_name)

        # Set up Lambda integration with API Gateway
        self._setup_lambda_integration()

        # Output API Gateway URL (CFN Output)
        CfnOutput(
            self, "VideoMakerWithNovaReelAPIGateway",
            value=self.api_gateway.url,
            description="The URL of the API Gateway"
        )

    def _create_s3_bucket(self, bucket_name: str) -> Bucket:
        """Creates an S3 bucket with CORS configuration."""
        return Bucket(
            self, "VideoMakerWithNovaReelBucket",
            bucket_name=bucket_name,
            removal_policy=RemovalPolicy.DESTROY,
            cors=[
                CorsRule(
                    allowed_methods=[
                        HttpMethods.GET,
                        HttpMethods.PUT,
                        HttpMethods.POST,
                        HttpMethods.DELETE,
                        HttpMethods.HEAD,
                    ],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                )
            ],
        )

    def _create_api_gateway(self) -> RestApi:
        """Creates an API Gateway."""
        return RestApi(
            self, "VideoMakerWithNovaReelApiGateway",
            rest_api_name="VideoMakerWithNovaReelApi",
            deploy_options={"stage_name": "prod"},
        )

    def _create_api_resources(self) -> None:
        """Configures API resources for video generation endpoint."""
        apis_resource = self.api_gateway.root.add_resource("apis")
        videos_resource = apis_resource.add_resource("videos")
        self.generate_resource = videos_resource.add_resource("generate")

    def _create_dependencies_layer(self) -> LayerVersion:
        """
        Creates a Lambda layer containing required dependencies.
        Installs packages defined in requirements file to a local directory,
        then uses that directory as the source for the Lambda layer.
        """
        requirements_file = "lambda/api/generate-video/requirements.txt"
        output_dir = ".build/layer"
        python_dir = os.path.join(output_dir, "python")
        os.makedirs(python_dir, exist_ok=True)
        subprocess.check_call(
            f"pip install -r {requirements_file} -t {python_dir}".split()
        )
        return LayerVersion(
            self,
            "DependenciesLayer",
            layer_version_name="dependencies-layer",
            code=Code.from_asset(output_dir),
        )

    def _create_video_lambda(self, model_id: str, bucket_name: str, layer: LayerVersion) -> Function:
        """Creates and configures Lambda function for video generation."""
        return Function(
            self,
            "VideoMakerWithNovaReelGenerateVideoLambda",
            function_name="VideoMakerWithNovaReelGenerateVideoLambda",
            runtime=Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=Code.from_asset("lambda/api/generate-video"),
            environment={
                "MODEL_ID": model_id,
                "S3_DESTINATION_BUCKET": bucket_name,
                "VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME": self.ddb_table_name,
            },
            timeout=Duration.seconds(30),
            layers=[layer],
        )

    def _attach_lambda_permissions(self, bucket_name: str) -> None:
        """Grants S3 and AWS Bedrock access permissions to Lambda function."""
        # Grant permissions for S3 PutObject and GetObject operations
        self.lambda_func.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["s3:PutObject", "s3:GetObject"],
                resources=[f"arn:aws:s3:::{bucket_name}/*"],
            )
        )
        # Grant permissions to call video generation model through AWS Bedrock
        self.lambda_func.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        # Grant DynamoDB PutItem Permission
        self.lambda_func.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["dynamodb:PutItem"],
                resources=["*"],
            )
        )

    def _setup_lambda_integration(self) -> None:
        """Connects API Gateway to Lambda function using Lambda integration."""
        integration = LambdaIntegration(self.lambda_func)
        self.generate_resource.add_method(
            "POST",
            integration,
            authorization_type=AuthorizationType.NONE,
            method_responses=[
                MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True,
                    },
                )
            ],
        )
