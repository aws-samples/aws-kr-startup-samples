from aws_cdk import (
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    custom_resources as cr,
    Duration,
)
from constructs import Construct
import os

class FashionStyleTableStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.ddb_generative_stylist_fashion_style_table_name = self.node.try_get_context("ddb_generative_stylist_fashion_style_table_name")
        
        # 기존 테이블 사용 여부 확인
        use_existing_tables = (self.node.try_get_context("use_existing_tables") == "true" or 
                              os.environ.get("USE_EXISTING_TABLES", "").lower() == "true")
        
        print(f"USE_EXISTING_TABLES: {use_existing_tables}")

        # 스타일 테이블 생성 또는 참조
        if use_existing_tables:
            self.fashion_style_table = dynamodb.Table.from_table_name(
                self, 'GenerativeStylistStyleTable',
                table_name=self.ddb_generative_stylist_fashion_style_table_name
            )
        else:
            self.fashion_style_table = dynamodb.Table(
                self, 'GenerativeStylistStyleTable',
                table_name=self.ddb_generative_stylist_fashion_style_table_name,
                partition_key=dynamodb.Attribute(
                    name='StyleName',
                    type=dynamodb.AttributeType.STRING
                ),
                removal_policy=RemovalPolicy.DESTROY,
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            )

            # Create GSI for Country
            self.fashion_style_table.add_global_secondary_index(
                index_name="CountryIndex",
                partition_key=dynamodb.Attribute(
                    name="Country",
                    type=dynamodb.AttributeType.STRING
                ),
                projection_type=dynamodb.ProjectionType.ALL,
            )

            
        # 테이블 이름을 CloudFormation 출력에 추가
        CfnOutput(self, 'GenerativeStylistFashionStyleTableName',
                 value=self.fashion_style_table.table_name,
                 description='GenerativeStylistFashionStyleTableName') 