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

class DDBStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.ddb_generative_stylist_image_process_table_name = self.node.try_get_context("ddb_generative_stylist_image_process_table_name")
        self.ddb_generative_stylist_image_display_table_name = self.node.try_get_context("ddb_generative_stylist_image_display_table_name")
        self.ddb_generative_stylist_fashion_style_table_name = self.node.try_get_context("ddb_generative_stylist_fashion_style_table_name")
        
        # 기존 테이블 사용 여부 확인 (컨텍스트 또는 환경 변수에서 가져옴)
        # 환경 변수나 컨텍스트에서 명시적으로 'true'를 받았을 때만 True가 되도록 수정
        use_existing_tables = (self.node.try_get_context("use_existing_tables") == "true" or 
                              os.environ.get("USE_EXISTING_TABLES", "").lower() == "true")
        
        print(f"USE_EXISTING_TABLES: {use_existing_tables}")  # 디버깅용 로그 추가
        

        # 스타일 테이블 생성 또는 참조
        if use_existing_tables:
            self.style_table = dynamodb.Table.from_table_name(
                self, 'GenerativeStylistStyleTable',
                table_name=self.ddb_generative_stylist_fashion_style_table_name
            )
        else:
            self.style_table = dynamodb.Table(
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
            self.style_table.add_global_secondary_index(
                index_name="CountryIndex",
                partition_key=dynamodb.Attribute(
                    name="Country",
                    type=dynamodb.AttributeType.STRING
                ),
                projection_type=dynamodb.ProjectionType.ALL,
            )

        # 프로세스 테이블 생성 또는 참조
        if use_existing_tables:
            self.process_table = dynamodb.Table.from_table_name(
                self, 'GenerativeStylistImageProcessTable',
                table_name=self.ddb_generative_stylist_image_process_table_name
            )
        else:
            self.process_table = dynamodb.Table(
                self, 'GenerativeStylistImageProcessTable',
                table_name=self.ddb_generative_stylist_image_process_table_name,
                partition_key=dynamodb.Attribute(
                    name='uuid',
                    type=dynamodb.AttributeType.STRING
                ),
                sort_key=dynamodb.Attribute(
                    name='userId',
                    type=dynamodb.AttributeType.STRING
                ),
                removal_policy=RemovalPolicy.DESTROY,
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            )

        # 디스플레이 테이블 생성 또는 참조
        if use_existing_tables:
            self.display_table = dynamodb.Table.from_table_name(
                self, 'GenerativeStylistImageDisplayTable',
                table_name=self.ddb_generative_stylist_image_display_table_name
            )
        else:
            self.display_table = dynamodb.Table(
                self, 'GenerativeStylistImageDisplayTable',
                table_name=self.ddb_generative_stylist_image_display_table_name,
                partition_key=dynamodb.Attribute(
                    name='userId',
                    type=dynamodb.AttributeType.STRING
                ),
                removal_policy=RemovalPolicy.DESTROY,
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            )
        
        # 테이블 이름을 CloudFormation 출력에 추가
        CfnOutput(self, 'GenerativeStylistImageProcessTableName',
                 value=self.process_table.table_name,
                 description='GenerativeStylistImageProcessTableName')
        CfnOutput(self, 'GenerativeStylistImageDisplayTableName',
                 value=self.display_table.table_name,
                 description='GenerativeStylistImageDisplayTableName')
        CfnOutput(self, 'GenerativeStylistStyleTableName',
                 value=self.style_table.table_name,
                 description='GenerativeStylistStyleTableName')



        