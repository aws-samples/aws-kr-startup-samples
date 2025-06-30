from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    Size,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_events,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_s3 as s3,
    RemovalPolicy,
    aws_s3_notifications as s3n,
    CustomResource,
)
from constructs import Construct
import os
from aws_cdk.custom_resources import Provider

class ImageProcessingLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.ddb_generative_stylist_image_process_table_name = self.node.try_get_context("ddb_generative_stylist_image_process_table_name")
        self.ddb_generative_stylist_image_display_table_name = self.node.try_get_context("ddb_generative_stylist_image_display_table_name")
        self.ddb_generative_stylist_fashion_style_table_name = self.node.try_get_context("ddb_generative_stylist_fashion_style_table_name")
        self.s3_base_bucket_name = self.node.try_get_context("s3_base_bucket_name")
        self.s3_face_object_path = self.node.try_get_context("s3_face_object_path")
        self.s3_face_cropped_object_path = self.node.try_get_context("s3_face_cropped_object_path")
        self.s3_face_swapped_object_path = self.node.try_get_context("s3_face_swapped_object_path")
        self.s3_result_object_path = self.node.try_get_context("s3_result_object_path")
        self.s3_theme_object_path = self.node.try_get_context("s3_theme_object_path")
        self.lambda_layer_s3_path = self.node.try_get_context("lambda_layer_s3_path")
        self.sagemaker_facechain_endpoint_name = self.node.try_get_context("facechain_sagemaker_endpoint_name")
        self.country = self.node.try_get_context("country")

        self.use_existing_resources = (self.node.try_get_context("use_existing_resources") == "true" or 
                                      os.environ.get("USE_EXISTING_RESOURCES", "").lower() == "true")
        
        print(f"USE_EXISTING_RESOURCES: {self.use_existing_resources}")

        # Create the face crop Lambda function
        self.face_crop_lambda = self.create_face_crop_lambda()

        # Create the face swap Lambda function
        self.face_swap_lambda = self.create_face_swap_lambda()

        # Create the face swap completion Lambda function
        self.face_swap_completion_lambda = self.create_face_swap_completion_lambda()
        
        # Configure S3 notifications after all Lambda functions are created
        self.configure_s3_notifications()

    def create_face_crop_lambda(self):
        """
        Create the face crop Lambda function and attach an S3 event source.
        """
        # Create the necessary layers
        pillow_layer_arn = self.node.try_get_context("pillow_layer_arn")
        pillow_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "PillowLayer",
            layer_version_arn=pillow_layer_arn
        )

        numpy_layer_arn = self.node.try_get_context("numpy_layer_arn")
        numpy_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "NumpyLayer",
            layer_version_arn=numpy_layer_arn
        )

        # Create the face-crop Lambda function inline
        lambda_func = lambda_.Function(
            self, "GenerativeStylistFaceCropLambda",
            function_name="GenerativeStylistFaceCropLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset("lambda/image-processing/face-crop"),
            environment={
                "BUCKET_NAME": self.s3_base_bucket_name,
                "FACE_CROPPED_OBJECT_PATH": self.s3_face_cropped_object_path
            },
            timeout=Duration.seconds(10),
            layers=[pillow_layer, numpy_layer]
        )

        # Grant permissions for S3 object put/get operations
        lambda_func.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:PutObject", "s3:GetObject"],
            resources=[
                f"arn:aws:s3:::{self.s3_base_bucket_name}/{self.s3_face_cropped_object_path}/*",
                f"arn:aws:s3:::{self.s3_base_bucket_name}/{self.s3_face_object_path}/*"
            ]
        ))

        # Grant permissions to invoke Rekognition APIs
        lambda_func.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["rekognition:DetectFaces", "rekognition:DetectLabels"],
            resources=["*"]
        ))

        return lambda_func

    def create_face_swap_lambda(self):
        """
        Create the face swap Lambda function
        """
        lambda_func = lambda_.Function(
            self, "GenerativeStylistFaceSwapLambda",
            function_name="GenerativeStylistFaceSwapLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset("lambda/image-processing/face-swap"),
            environment={
                "BUCKET_NAME": self.s3_base_bucket_name,
                "RESULT_OBJECT_PATH": self.s3_result_object_path,
                "SAGEMAKER_FACECHAIN_ENDPOINT_NAME": self.sagemaker_facechain_endpoint_name,
                "DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME": self.ddb_generative_stylist_image_process_table_name,
                "DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME": self.ddb_generative_stylist_fashion_style_table_name,
                "COUNTRY": self.country
            },
            timeout=Duration.seconds(60)
        )

        # Grant permissions for DynamoDB operations
        lambda_func.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[                
                "dynamodb:PutItem", 
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:GetItem"
            ],
            resources=[
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_image_process_table_name}",
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_fashion_style_table_name}",
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_fashion_style_table_name}/index/*"
            ]
        ))

        # Grant PutObject permission for S3 bucket
        lambda_func.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:PutObject"],
            resources=[
                f"arn:aws:s3:::{self.s3_base_bucket_name}/*"
            ]
        ))

        # Grant SageMaker endpoint invoke permission
        lambda_func.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sagemaker:InvokeEndpoint"],
            resources=[
                f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/{self.sagemaker_facechain_endpoint_name}",
            ]
        ))

        # Grant permissions for S3 object put/get operations
        lambda_func.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
            resources=[
                f"arn:aws:s3:::{self.s3_base_bucket_name}/{self.s3_face_cropped_object_path}/*",
                f"arn:aws:s3:::{self.s3_base_bucket_name}/{self.s3_face_swapped_object_path}/*"
            ]
        ))

        # Grant permissions for Amazon Bedrock operations
        lambda_func.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            resources=["*"]
        ))

        return lambda_func

    def create_face_swap_completion_lambda(self):
        """
        Create the face swap completion Lambda function using a Lambda layer for dependencies.
        """
        lambda_func = lambda_.Function(
            self, "GenerativeStylistFaceSwapCompletionLambda",
            function_name="GenerativeStylistFaceSwapCompletionLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset("lambda/image-processing/face-swap-completion"),
            environment={
                "DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME": self.ddb_generative_stylist_image_process_table_name,
                "DDB_GENERATIVE_STYLIST_IMAGE_DISPLAY_TABLE_NAME": self.ddb_generative_stylist_image_display_table_name
            },
            timeout=Duration.seconds(60)
        )

        # Grant permissions for DynamoDB operations
        lambda_func.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "dynamodb:PutItem", 
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:GetItem"
            ],
            resources=[
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_image_process_table_name}",
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_image_process_table_name}/index/*",
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_image_display_table_name}",
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_image_display_table_name}/index/*"
            ]
        ))

        # Grant permissions for S3 bucket and object operations
        lambda_func.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            resources=[
                f"arn:aws:s3:::{self.s3_base_bucket_name}",
                f"arn:aws:s3:::{self.s3_base_bucket_name}/*"
            ]
        ))

        return lambda_func

    def configure_s3_notifications(self):
        """
        Configure all S3 event notifications in a single operation to avoid conflicts.
        """
        print(f"S3 버킷 '{self.s3_base_bucket_name}'에 대한 알림 구성 설정 중...")
        
        # 경로에 / 문자가 없는 경우 추가
        face_object_path = self.s3_face_object_path if self.s3_face_object_path.endswith('/') else f"{self.s3_face_object_path}/"
        face_cropped_object_path = self.s3_face_cropped_object_path if self.s3_face_cropped_object_path.endswith('/') else f"{self.s3_face_cropped_object_path}/"
        result_object_path = self.s3_result_object_path if self.s3_result_object_path.endswith('/') else f"{self.s3_result_object_path}/"
        
        # Lambda 함수에 권한 부여 (이름 충돌 방지를 위해 고유한 ID 사용)
        self.face_crop_lambda.add_permission(
            "S3InvokeFaceCrop-" + self.node.addr,
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:s3:::{self.s3_base_bucket_name}"
        )
        
        self.face_swap_lambda.add_permission(
            "S3InvokeFaceSwap-" + self.node.addr,
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:s3:::{self.s3_base_bucket_name}"
        )
        
        self.face_swap_completion_lambda.add_permission(
            "S3InvokeFaceCompletion-" + self.node.addr,
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:s3:::{self.s3_base_bucket_name}"
        )
        
        # 버킷 참조 생성
        bucket = s3.Bucket.from_bucket_name(
            self,
            "NotificationsBucket",
            bucket_name=self.s3_base_bucket_name
        )
        
        # 저수준 CustomResource를 사용하여 S3 알림 구성
        configure_notifications_lambda = lambda_.Function(
            self, 
            "ConfigureS3NotificationsLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import boto3
import cfnresponse
import json

def handler(event, context):
    props = event['ResourceProperties']
    bucket_name = props['BucketName']
    notification_config = {
        'LambdaFunctionConfigurations': [
            {
                'Events': ['s3:ObjectCreated:Put'],
                'LambdaFunctionArn': props['FaceCropLambdaArn'],
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {
                                'Name': 'prefix',
                                'Value': props['FaceObjectPath']
                            }
                        ]
                    }
                }
            },
            {
                'Events': ['s3:ObjectCreated:Put'],
                'LambdaFunctionArn': props['FaceSwapLambdaArn'],
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {
                                'Name': 'prefix',
                                'Value': props['FaceCroppedObjectPath'] 
                            }
                        ]
                    }
                }
            },
            {
                'Events': ['s3:ObjectCreated:Put'],
                'LambdaFunctionArn': props['FaceSwapCompletionLambdaArn'],
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {
                                'Name': 'prefix',
                                'Value': props['ResultObjectPath']
                            }
                        ]
                    }
                }
            }
        ]
    }
    
    if event['RequestType'] in ['Create', 'Update']:
        try:
            s3 = boto3.client('s3')
            s3.put_bucket_notification_configuration(
                Bucket=bucket_name,
                NotificationConfiguration=notification_config
            )
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        except Exception as e:
            print(f"Error configuring bucket notifications: {str(e)}")
            cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
    elif event['RequestType'] == 'Delete':
        try:
            s3 = boto3.client('s3')
            s3.put_bucket_notification_configuration(
                Bucket=bucket_name,
                NotificationConfiguration={}
            )
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        except Exception as e:
            print(f"Error clearing bucket notifications: {str(e)}")
            cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
        """),
            timeout=Duration.seconds(30)
        )
        
        # S3 권한 추가
        configure_notifications_lambda.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:PutBucketNotification", "s3:GetBucketNotification"],
            resources=[f"arn:aws:s3:::{self.s3_base_bucket_name}"]
        ))
        
        # 커스텀 리소스 프로바이더 생성
        provider = Provider(
            self,
            "S3NotificationsProvider",
            on_event_handler=configure_notifications_lambda
        )
        
        # 커스텀 리소스를 통해 S3 알림 구성
        CustomResource(
            self,
            "S3NotificationsConfig",
            service_token=provider.service_token,
            properties={
                "BucketName": self.s3_base_bucket_name,
                "FaceCropLambdaArn": self.face_crop_lambda.function_arn,
                "FaceSwapLambdaArn": self.face_swap_lambda.function_arn,
                "FaceSwapCompletionLambdaArn": self.face_swap_completion_lambda.function_arn,
                "FaceObjectPath": face_object_path,
                "FaceCroppedObjectPath": face_cropped_object_path,
                "ResultObjectPath": result_object_path
            }
        )
        
        print(f"S3 버킷 '{self.s3_base_bucket_name}'에 대한 알림 구성이 성공적으로 설정되었습니다.")
