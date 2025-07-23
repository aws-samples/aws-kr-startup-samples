#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_synthetics as synthetics,
    aws_iam as iam,
    aws_s3 as s3
)
from constructs import Construct


class SyntheticsStack(Stack):
    """CloudWatch Synthetics Canary를 생성하는 스택"""

    def __init__(self, scope: Construct, construct_id: str,
                 canary_artifact_bucket: s3.Bucket,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.canary_artifact_bucket = canary_artifact_bucket

        # Canary Execution Role
        self.canary_execution_role = iam.Role(
            self, "CanaryExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            path="/",
            inline_policies={
                "can-execute-canary": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["s3:PutObject"],
                            resources=[f"{self.canary_artifact_bucket.bucket_arn}/*"]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetBucketLocation",
                                "s3:ListAllMyBuckets",
                                "cloudwatch:PutMetricData",
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "ec2:CreateNetworkInterface",
                                "ec2:DescribeNetworkInterfaces",
                                "ec2:DeleteNetworkInterface"
                            ],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["*"],
                            resources=["*"]
                        )
                    ]
                )
            }
        )

        # Synthetics Canary (최신 런타임 버전 사용)
        self.canary = synthetics.CfnCanary(
            self, "Canary",
            name="create-more-spice",
            artifact_s3_location=f"s3://{self.canary_artifact_bucket.bucket_name}/canary",
            execution_role_arn=self.canary_execution_role.role_arn,
            runtime_version="syn-python-selenium-2.1",  # 최신 버전으로 업데이트
            schedule=synthetics.CfnCanary.ScheduleProperty(
                expression="rate(0 hour)",  # Run once
                duration_in_seconds="0"
            ),
            code=synthetics.CfnCanary.CodeProperty(
                handler="lambda_function.handler",
                script=self._get_canary_script()
            ),
            start_canary_after_creation=True
        )

        # 출력값
        cdk.CfnOutput(
            self, "CanaryName",
            value=self.canary.name,
            export_name=f"{self.stack_name}-CanaryName"
        )
        
        cdk.CfnOutput(
            self, "CanaryArn",
            value=self.canary.ref,
            export_name=f"{self.stack_name}-CanaryArn"
        )

    def _get_canary_script(self) -> str:
        """Canary 스크립트 코드 (QuickSight 관련 제거)"""
        return '''
import time
import json
import urllib3
from urllib import parse
import os
import boto3
from selenium.webdriver.common.by import By
from aws_synthetics.selenium import synthetics_webdriver as syn_webdriver
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    logger.info("Starting Canary execution")
    
    try:
        # 기본적인 헬스체크 수행
        driver = syn_webdriver.Chrome()
        driver.get("https://aws.amazon.com")
        time.sleep(5)
        
        # 페이지 타이틀 확인
        title = driver.title
        logger.info(f"Page title: {title}")
        
        if "Amazon Web Services" in title:
            logger.info("Health check passed")
        else:
            raise Exception("Health check failed")
        
        driver.quit()
        logger.info("Canary execution completed successfully")
        
    except Exception as e:
        logger.error(f"Canary execution failed: {e}")
        raise e
'''
