import os
import subprocess
import uuid
from aws_cdk import (
    Aws,
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
from aws_cdk.aws_events import Rule, Schedule
from aws_cdk.aws_events_targets import LambdaFunction


class VideoMakerWithNovaReelStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get context information
        self.video_generation_model_id = self.node.try_get_context("video_generation_model_id")
        self.s3_stack_bucket_name = self.node.try_get_context("s3_base_bucket_name")
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
        self.generate_video_lambda = self._create_generate_video_lambda(
            model_id=self.video_generation_model_id,
            bucket_name=self.s3_stack_bucket_name,
            layer=dependencies_layer
        )

        # Add dependency to ensure Lambda function is created after S3 bucket
        self.generate_video_lambda.node.add_dependency(self.s3_base_bucket)
        self.generate_video_lambda.node.add_dependency(self.video_maker_with_nova_reel_process_table)  # DynamoDB 의존성 추가
        self.api_gateway.node.add_dependency(self.generate_video_lambda)

        # Grant S3, AWS Bedrock, and DynamoDB permissions to Lambda function
        self._attach_generate_video_lambda_permissions(self.s3_stack_bucket_name)

        # Set up Lambda integration with API Gateway for video generation
        self._setup_generate_video_lambda_integration()

        # Create video listing Lambda function
        self.list_videos_lambda = self._create_list_videos_lambda()

        # Add dependency to ensure Lambda function is created after S3 bucket
        self.list_videos_lambda.node.add_dependency(self.s3_base_bucket)

        # Grant DynamoDB permissions to listing Lambda function
        self._attach_list_videos_lambda_permissions()

        # Set up Lambda integration with API Gateway for video listing
        self._setup_list_videos_lambda_integration()

        # Create get video Lambda function
        self.get_video_lambda = self._create_get_video_lambda()

        # Add dependency to ensure Lambda function is created after S3 bucket
        self.get_video_lambda.node.add_dependency(self.s3_base_bucket)

        # Grant S3 permissions to get video Lambda function
        self._attach_get_video_lambda_permissions()

        # Set up Lambda integration with API Gateway for getting video
        self._setup_get_video_by_invocation_id_integration()
        
        # Create status check Lambda function
        self.status_videos_lambda = self._create_status_videos_lambda(dependencies_layer)

        # Add dependency to ensure Lambda function is created after S3 bucket
        self.status_videos_lambda.node.add_dependency(self.s3_base_bucket)

        # Grant permissions to status check Lambda function
        self._attach_status_videos_lambda_permissions(self.s3_stack_bucket_name)

        # Create EventBridge rule for status check
        self._create_status_check_rule()
        
        # Output API Gateway URL (CFN Output)
        CfnOutput(
            self, "VideoMakerWithNovaReelAPIGateway",
            value=self.api_gateway.url,
            description="The URL of the API Gateway"
        )

    def _create_status_check_rule(self) -> None:
        """Creates EventBridge rule to trigger status check Lambda."""
        Rule(
            self,
            "VideoStatusCheckRule",
            schedule=Schedule.rate(Duration.minutes(1)),
            targets=[LambdaFunction(self.status_videos_lambda)]
        )

    def _create_s3_bucket(self, bucket_name: str) -> Bucket:
        """Creates an S3 bucket with CORS configuration."""
        return Bucket(
            self, "VideoMakerWithNovaReelBucket",
            bucket_name=bucket_name,
            removal_policy=RemovalPolicy.RETAIN,
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
        """Configures API resources for video generation endpoint and video listing."""
        apis_resource = self.api_gateway.root.add_resource("apis")
        self.videos_resource = apis_resource.add_resource("videos")
        self.generate_resource = self.videos_resource.add_resource("generate")
        self.video_with_id_resource = self.videos_resource.add_resource("{invocation_id}")

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
            ["pip", "install", "-r", requirements_file, "-t", python_dir]
        )
        return LayerVersion(
            self,
            "DependenciesLayer",
            layer_version_name="dependencies-layer",
            code=Code.from_asset(output_dir),
        )

    def _create_generate_video_lambda(self, model_id: str, bucket_name: str, layer: LayerVersion) -> Function:
        """Generate video and configures Lambda function for video generation."""
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

    def _create_list_videos_lambda(self) -> Function:
        """Create and configure Lambda function for video listing."""
        return Function(
            self,
            "VideoMakerWithNovaReelListVideosLambda",
            function_name="VideoMakerWithNovaReelListVideosLambda",
            runtime=Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=Code.from_asset("lambda/api/list-video"),
            environment={
                "VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME": self.ddb_table_name,
            },
        )
    
    def _create_status_videos_lambda(self, layer: LayerVersion) -> Function:
        """Create and configure Lambda function for checking video status."""
        return Function(
            self,
            "VideoMakerWithNovaReelStatusVideosLambda",
            function_name="VideoMakerWithNovaReelStatusVideosLambda",
            runtime=Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=Code.from_asset("lambda/api/status-video"),
            environment={
                "VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME": self.ddb_table_name,
            },
            timeout=Duration.minutes(1),
            layers=[layer],
        )

    def _create_get_video_lambda(self) -> Function:
        """Create and configure Lambda function for getting video."""
        return Function(
            self,
            "VideoMakerWithNovaReelGetVideoLambda",
            function_name="VideoMakerWithNovaReelGetVideoLambda",
            runtime=Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=Code.from_asset("lambda/api/get-video"),
            environment={
                "VIDEO_MAKER_WITH_NOVA_REEL_PROCESS_TABLE_NAME": self.ddb_table_name
            },
        )
    
    def _attach_generate_video_lambda_permissions(self, bucket_name: str) -> None:
        """Grants S3, AWS Bedrock, and DynamoDB access permissions to the video generation Lambda function."""
        # Grant permissions for S3 PutObject and GetObject operations
        self.generate_video_lambda.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["s3:PutObject", "s3:GetObject"],
                resources=[f"arn:aws:s3:::{bucket_name}/*"],
            )
        )
        # Grant permissions to call video generation model through AWS Bedrock
        self.generate_video_lambda.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )
        # Grant DynamoDB PutItem Permission (제한된 테이블 ARN으로 설정)
        self.generate_video_lambda.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["dynamodb:PutItem"],
                resources=[self.video_maker_with_nova_reel_process_table.table_arn],
            )
        )

    def _attach_status_videos_lambda_permissions(self, bucket_name: str) -> None:
        """Grants required permissions to the status check Lambda function."""
        self.status_videos_lambda.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject"
                ],
                resources=[f"arn:aws:s3:::{bucket_name}/*"],
            )
        )
        
        self.status_videos_lambda.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:ListAsyncInvokes",
                    "bedrock:GetAsyncInvoke"
                ],
                resources=["*"],
            )
        )
        
        self.status_videos_lambda.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    "dynamodb:PutItem",
                    "dynamodb:Scan",
                    "dynamodb:UpdateItem"
                ],
                resources=[self.video_maker_with_nova_reel_process_table.table_arn],
            )
        )

    def _setup_generate_video_lambda_integration(self) -> None:
        """Connects API Gateway to the video generation Lambda function using Lambda integration."""
        integration = LambdaIntegration(self.generate_video_lambda)
        self.generate_resource.add_method(
            "POST",
            integration,
            authorization_type=AuthorizationType.NONE,
            method_responses=self._default_method_response()
        )
    
    def _attach_list_videos_lambda_permissions(self) -> None:
        """Grants DynamoDB scan permission to the video listing Lambda function (제한된 테이블 ARN으로 설정)."""
        self.list_videos_lambda.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["dynamodb:Scan"],
                resources=[self.video_maker_with_nova_reel_process_table.table_arn],
            )
        )

    def _attach_get_video_lambda_permissions(self) -> None:
        """Grants DynamoDB GetItem permission to the get video Lambda function."""
        self.get_video_lambda.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["dynamodb:GetItem"],
                resources=[self.video_maker_with_nova_reel_process_table.table_arn],
            )
        )
        """Grants S3 GetObject and ListBucket permission to the get video Lambda function."""
        self.get_video_lambda.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    self.s3_base_bucket.bucket_arn,
                    f"{self.s3_base_bucket.bucket_arn}/*"
                ],
            )
        )

    def _setup_list_videos_lambda_integration(self) -> None:
        """Connects API Gateway to the video listing Lambda function using Lambda integration."""
        integration = LambdaIntegration(
            self.list_videos_lambda,
            proxy=True,
            integration_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': "'*'",
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,OPTIONS'"
                }
            }]
        )
        self.videos_resource.add_method(
            "GET",
            integration,
            authorization_type=AuthorizationType.NONE,
            method_responses=self._default_method_response()
        )
        self.videos_resource.add_cors_preflight(
            allow_origins=["*"],
            allow_methods=["GET", "OPTIONS"],
            allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token", "Access-Control-Allow-Origin", "Access-Control-Allow-Headers", "Access-Control-Allow-Methods"]
        )
    
    def _setup_get_video_by_invocation_id_integration(self) -> None:
        """Connects API Gateway to the get video Lambda function using Lambda integration."""
        integration = LambdaIntegration(
            self.get_video_lambda,
            proxy=True,
            integration_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': "'*'",
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,OPTIONS'"
                }
            }]
        )
        self.video_with_id_resource.add_method(
            "GET",
            integration,
            authorization_type=AuthorizationType.NONE,
            method_responses=self._default_method_response()
        )
        # CORS preflight 설정 추가
        self.video_with_id_resource.add_cors_preflight(
            allow_origins=["*"],
            allow_methods=["GET", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "X-Amz-Date",
                "Authorization",
                "X-Api-Key",
                "X-Amz-Security-Token",
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Headers",
                "Access-Control-Allow-Methods"
            ],
        )
    
    def _default_method_response(self):
        """Returns a default MethodResponse configuration for CORS."""
        return [
            MethodResponse(
                status_code="200",
                response_parameters={
                    "method.response.header.Access-Control-Allow-Origin": True, 
                    "method.response.header.Access-Control-Allow-Headers": True,
                    "method.response.header.Access-Control-Allow-Methods": True,
                },
            )
        ]
