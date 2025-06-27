from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    aws_ssm as ssm,
    aws_iam as iam
)
from constructs import Construct
import os

class ApiGatewayStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Retrieve S3 bucket name and object path from context
        self.s3_base_bucket_name = self.node.try_get_context("s3_base_bucket_name")
        self.s3_face_object_path = self.node.try_get_context("s3_face_object_path")
        self.ddb_generative_stylist_image_process_table_name = self.node.try_get_context("ddb_generative_stylist_image_process_table_name")
        self.ddb_generative_stylist_image_display_table_name = self.node.try_get_context("ddb_generative_stylist_image_display_table_name")
        self.ddb_generative_stylist_fashion_style_table_name = self.node.try_get_context("ddb_generative_stylist_fashion_style_table_name")

        # Create API Gateway
        self.api_gateway = self.create_api_gateway()

        # Create API resources: /apis/images/upload
        apis_resource = self.api_gateway.root.add_resource("apis")
        images_resource = apis_resource.add_resource("images")
        self.upload_resource = images_resource.add_resource("upload")

        # Create Lambda function for handling image uploads
        self.upload_lambda = self.create_image_upload_lambda_function(
            lambda_path="lambda/apis/put-image", 
            object_path=self.s3_face_object_path
        )

        # Set up Lambda integration for the upload resource
        upload_integration = apigw.LambdaIntegration(self.upload_lambda)
        
        # Add POST method
        self.upload_resource.add_method(
            "POST",
            upload_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True
                    }
                )
            ]
        )

        # Create API resources: /apis/images/{userId}
        self.get_image_resource = images_resource.add_resource("{userId}")

        # Create Lambda function for handling video generation
        self.get_image_lambda = self.create_get_image_lambda_function(
            lambda_path="lambda/apis/get-image"
        )

        # Set up Lambda integration for the get image resource
        get_image_integration = apigw.LambdaIntegration(self.get_image_lambda)  
        
        # Add GET method
        self.get_image_resource.add_method(
            "GET",
            get_image_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True
                    }
                )
            ]
        )

        # Create API resources: /apis/styles
        styles_resource = apis_resource.add_resource("styles")
        
        # Create Lambda function for getting styles
        self.get_styles_lambda = self.create_get_styles_lambda_function(
            lambda_path="lambda/apis/get-styles"
        )

        # Set up Lambda integration for the styles resource
        get_styles_integration = apigw.LambdaIntegration(self.get_styles_lambda)

        # Add GET method for styles
        styles_resource.add_method(
            "GET",
            get_styles_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True
                    }
                )
            ]
        )

        # Output the API Gateway URL as a CloudFormation output
        self.create_output()

    def create_api_gateway(self):
        """Create and return the API Gateway."""
        return apigw.RestApi(
            self, "GenerativeStylistImageAPI",
            rest_api_name="GenerativeStylistImageAPI",
            description="This service processes images.",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"]
            )
        )

    def create_get_styles_lambda_function(self, lambda_path):
        """Create and return a Lambda function for getting styles."""
        lambda_function = lambda_.Function(
            self, "GenerativeStylistGetStyles",
            function_name="GenerativeStylistGetStyles",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(lambda_path),
            environment={
                "DDB_GENERATIVE_STYLIST_FASHION_STYLE_TABLE_NAME": self.ddb_generative_stylist_fashion_style_table_name
            },
            timeout=Duration.seconds(30)
        )
        
        # Grant permission to read from the StyleTable
        lambda_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["dynamodb:Scan", "dynamodb:Query"],
            resources=[
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_fashion_style_table_name}",
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_fashion_style_table_name}/index/*"
            ]
        ))
        
        return lambda_function

    def create_get_image_lambda_function(self, lambda_path):
        """Create and return a Lambda function with appropriate permissions."""
        lambda_function = lambda_.Function(
            self, "GenerativeStylistGetImage",
            function_name="GenerativeStylistGetImage",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(lambda_path),
            environment={
                "BUCKET_NAME": self.s3_base_bucket_name,
                "DDB_GENERATIVE_STYLIST_IMAGE_DISPLAY_TABLE_NAME": self.ddb_generative_stylist_image_display_table_name
            },
            timeout=Duration.seconds(10)
        )
        
        # Grant permission to put objects in the specified S3 bucket path
        lambda_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject"],
            resources=[f"arn:aws:s3:::{self.s3_base_bucket_name}/*"]
        ))

        # Grant permission to put items in the specified DDB table
        lambda_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["dynamodb:GetItem", "dynamodb:Query"],
            resources=[
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_image_display_table_name}",
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_fashion_style_table_name}"
            ]
        ))
        
        return lambda_function

    def create_image_upload_lambda_function(self, lambda_path, object_path):
        """Create and return a Lambda function with appropriate permissions."""
        lambda_function = lambda_.Function(
            self, "GenerativeStylistUploadImage",
            function_name="GenerativeStylistUploadImage",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(lambda_path),
            environment={
                "BUCKET_NAME": self.s3_base_bucket_name,
                "OBJECT_PATH": object_path,
                "DDB_GENERATIVE_STYLIST_STYLE_TABLE_NAME": self.ddb_generative_stylist_fashion_style_table_name,
                "DDB_GENERATIVE_STYLIST_IMAGE_PROCESS_TABLE_NAME": self.ddb_generative_stylist_image_process_table_name
            },
            timeout=Duration.seconds(10)
        )
        
        # Grant permission to put objects in the specified S3 bucket path
        lambda_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:PutObject"],
            resources=[f"arn:aws:s3:::{self.s3_base_bucket_name}/{object_path}/*"]
        ))

        # Grant permission to put items in the specified DDB table
        lambda_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query"],
            resources=[
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_fashion_style_table_name}",
                f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.ddb_generative_stylist_image_process_table_name}"
            ]
        ))
        
        return lambda_function

    def create_output(self):
        """Create CloudFormation output for the API Gateway URL."""
        CfnOutput(
            self, "GenerativeStylistApiGatewayOutput",
            value=self.api_gateway.url,
            description="The URL of the API Gateway"
        )