#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    RemovalPolicy
)
from constructs import Construct


class S3Stack(Stack):
    """S3 버킷들을 생성하는 스택"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Athena Data Lake S3 Bucket
        self.athena_data_lake = s3.Bucket(
            self, "AthenaDataLakeBucket",
            bucket_name=f"athena-data-lake-bucket-{self.account}",
            removal_policy=RemovalPolicy.DESTROY,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

        # Canary Artifact S3 Bucket  
        self.canary_artifact_bucket = s3.Bucket(
            self, "CanaryArtifactBucket",
            bucket_name=f"cid-{self.account}-canary",
            removal_policy=RemovalPolicy.DESTROY,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

        # 속성으로 버킷 이름 저장
        self.athena_data_lake_bucket_name = self.athena_data_lake.bucket_name
        self.canary_artifact_bucket_name = self.canary_artifact_bucket.bucket_name

        # 출력값
        cdk.CfnOutput(
            self, "AthenaDataLakeBucketName",
            value=self.athena_data_lake.bucket_name,
            export_name=f"{self.stack_name}-AthenaDataLakeBucketName"
        )
        
        cdk.CfnOutput(
            self, "CanaryArtifactBucketName", 
            value=self.canary_artifact_bucket.bucket_name,
            export_name=f"{self.stack_name}-CanaryArtifactBucketName"
        )
