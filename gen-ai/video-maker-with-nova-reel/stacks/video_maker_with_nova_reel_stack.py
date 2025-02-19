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

        # Context 정보를 가져옵니다.
        self.video_generation_model_id = self.node.try_get_context("video_generation_model_id")
        self.s3_base_bucket_name = self.node.try_get_context("s3_base_bucket_name")
        self.s3_stack_bucket_name = f"{self.s3_base_bucket_name}-{self.node.id}".lower()
        self.ddb_table_name = self.node.try_get_context("video_maker_with_nova_reel_process_table")

        # DynamoDB 테이블 생성
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

        # CORS 설정을 갖춘 S3 버킷 생성
        self.s3_base_bucket = self._create_s3_bucket(self.s3_stack_bucket_name)

        # S3 버킷 이름 출력(CFN Output)
        CfnOutput(
            self, "VideoMakerWithNovaReelS3Bucket",
            value=self.s3_base_bucket.bucket_name,
            description="The name of the S3 bucket used by the VideoMakerWithNovaReel application"
        )

        # API Gateway 및 리소스 생성
        self.api_gateway = self._create_api_gateway()
        self._create_api_resources()

        # Lambda 레이어 (dependencies) 생성
        dependencies_layer = self._create_dependencies_layer()

        # 비디오 생성 Lambda 함수 생성
        self.lambda_func = self._create_video_lambda(
            model_id=self.video_generation_model_id,
            bucket_name=self.s3_stack_bucket_name,
            layer=dependencies_layer
        )

        # Lambda 함수가 S3 버킷 생성 이후에 생성되도록 의존성 추가
        self.lambda_func.node.add_dependency(self.s3_base_bucket)

        # Lambda 함수에 S3 및 AWS Bedrock 권한 부여
        self._attach_lambda_permissions(self.s3_stack_bucket_name)

        # API Gateway와 Lambda 함수 통합 설정
        self._setup_lambda_integration()

        # API Gateway URL 출력(CFN Output)
        CfnOutput(
            self, "VideoMakerWithNovaReelAPIGateway",
            value=self.api_gateway.url,
            description="The URL of the API Gateway"
        )

    def _create_s3_bucket(self, bucket_name: str) -> Bucket:
        """CORS 설정을 가진 S3 버킷을 생성합니다."""
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
        """API Gateway를 생성합니다."""
        return RestApi(
            self, "VideoMakerWithNovaReelApiGateway",
            rest_api_name="VideoMakerWithNovaReelApi",
            deploy_options={"stage_name": "prod"},
        )

    def _create_api_resources(self) -> None:
        """비디오 생성 엔드포인트용 API 리소스를 구성합니다."""
        apis_resource = self.api_gateway.root.add_resource("apis")
        videos_resource = apis_resource.add_resource("videos")
        self.generate_resource = videos_resource.add_resource("generate")

    def _create_dependencies_layer(self) -> LayerVersion:
        """
        필요한 의존성을 포함하는 Lambda 레이어를 생성합니다.
        requirements 파일에 정의된 패키지들을 로컬 디렉토리에 설치 후, 해당 디렉토리를 Lambda 레이어의 소스로 사용합니다.
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
        """비디오 생성을 위한 Lambda 함수를 생성 및 구성합니다."""
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
        """Lambda 함수에 S3 및 AWS Bedrock 접근 권한을 부여합니다."""
        # S3 PutObject 및 GetObject 작업에 대한 권한 부여
        self.lambda_func.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["s3:PutObject", "s3:GetObject"],
                resources=[f"arn:aws:s3:::{bucket_name}/*"],
            )
        )
        # AWS Bedrock을 통해 비디오 생성 모델 호출 권한 부여
        self.lambda_func.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

    def _setup_lambda_integration(self) -> None:
        """API Gateway와 Lambda 함수를 Lambda 통합을 이용하여 연결합니다."""
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
