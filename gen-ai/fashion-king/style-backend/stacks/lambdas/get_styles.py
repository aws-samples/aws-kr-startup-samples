from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam
)
from constructs import Construct

class GetStylesLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 테이블 이름 가져오기
        self.ddb_generative_stylist_fashion_style_table_name = self.node.try_get_context("ddb_generative_stylist_fashion_style_table_name")

        # Lambda 함수 생성
        self.get_styles_lambda = self.create_get_styles_lambda_function(
            lambda_path="lambda/apis/get-styles"
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