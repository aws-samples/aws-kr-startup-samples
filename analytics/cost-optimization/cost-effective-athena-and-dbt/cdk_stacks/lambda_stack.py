#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
    Duration
)
from constructs import Construct


class LambdaStack(Stack):
    """Lambda 함수들을 생성하는 스택"""

    def __init__(self, scope: Construct, construct_id: str,
                 vpc: ec2.Vpc,
                 aurora_hostname: str,
                 aurora_secret_arn: str,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = vpc
        self.aurora_hostname = aurora_hostname
        self.aurora_secret_arn = aurora_secret_arn

        # MySQL Client 보안 그룹 가져오기 (Aurora 접근용)
        self.mysql_client_sg = ec2.SecurityGroup.from_security_group_id(
            self, "MySQLClientSG",
            security_group_id=cdk.Fn.import_value("AuroraMysqlStack:ExportsOutputFnGetAttMySQLClientSG7594693AGroupIdAA3A79F1")
        )

        # Lambda Layer (로컬 assets 사용)
        self.lambda_layer = _lambda.LayerVersion(
            self, "LambdaLayer",
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_10],
            description="Lambda layer for Python dependencies",
            code=_lambda.Code.from_asset(
                os.path.join(os.path.dirname(__file__), '../assets/lambda/layers/python')
            )
        )

        # Sales Generator Lambda 역할
        self.sales_generator_lambda_role = iam.Role(
            self, "SalesGeneratorLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ],
            inline_policies={
                "SecretsManagerAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["secretsmanager:GetSecretValue"],
                            resources=[self.aurora_secret_arn]
                        )
                    ]
                )
            }
        )

        # Sales Generator Lambda 함수 (로컬 assets 사용)
        self.sales_generator_lambda = _lambda.Function(
            self, "SalesGeneratorLambda",
            runtime=_lambda.Runtime.PYTHON_3_10,
            function_name="sales-generator",
            handler="salesgenerator.lambda_handler",
            description="Lambda function for generating sales data",
            code=_lambda.Code.from_asset(
                os.path.join(os.path.dirname(__file__), '../assets/lambda/functions/sales-generator')
            ),
            layers=[self.lambda_layer],
            role=self.sales_generator_lambda_role,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[self.mysql_client_sg],  # MySQL Client SG 사용
            timeout=Duration.seconds(60),
            memory_size=128,
            environment={
                "LOG_LEVEL": "INFO",
                "HOST": self.aurora_hostname,
                "DATABASE": "mysql",  # 기본 mysql DB 사용 (rds DB 생성용)
                "SECRET_ARN": self.aurora_secret_arn
            }
        )

        # EventBridge 규칙 (2분마다 실행)
        self.step_trigger = events.Rule(
            self, "StepTrigger",
            description="Trigger sales generator lambda every 2 minutes",
            schedule=events.Schedule.rate(Duration.minutes(2))
        )

        # Lambda 함수를 EventBridge 타겟으로 추가
        self.step_trigger.add_target(
            targets.LambdaFunction(self.sales_generator_lambda)
        )

        # 출력값
        cdk.CfnOutput(
            self, "SalesGeneratorLambdaArn",
            value=self.sales_generator_lambda.function_arn,
            export_name=f"{self.stack_name}-SalesGeneratorLambdaArn"
        )
        
        cdk.CfnOutput(
            self, "LambdaLayerArn",
            value=self.lambda_layer.layer_version_arn,
            export_name=f"{self.stack_name}-LambdaLayerArn"
        )
