#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_glue as glue,
    aws_iam as iam,
    aws_s3 as s3
)
from constructs import Construct


class GlueCrawlerStack(Stack):
    """Glue Crawler를 생성하는 스택"""

    def __init__(self, scope: Construct, construct_id: str,
                 athena_data_lake_bucket: s3.Bucket,
                 raw_data_database_name: str,
                 raw_data_s3_prefix: str = "raw_data",
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.athena_data_lake_bucket = athena_data_lake_bucket
        self.raw_data_database_name = raw_data_database_name
        self.raw_data_s3_prefix = raw_data_s3_prefix

        # CSV Classifier
        self.csv_classifier = glue.CfnClassifier(
            self, "CSVClassifier",
            csv_classifier=glue.CfnClassifier.CsvClassifierProperty(
                name="csvClassifier",
                delimiter=",",
                quote_symbol='"',
                contains_header="PRESENT",
                disable_value_trimming=False,
                allow_single_column=False
            )
        )

        # Ticket Crawler Role
        self.ticket_crawler_role = iam.Role(
            self, "TicketCrawlerRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            description="Glue crawler role for ticket data",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")
            ],
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                f"{self.athena_data_lake_bucket.bucket_arn}/{self.raw_data_s3_prefix}/ticket/*"
                            ]
                        )
                    ]
                )
            }
        )

        # Ticket Crawler
        self.ticket_crawler = glue.CfnCrawler(
            self, "TicketCrawler",
            name="TicketCrawler",
            role=self.ticket_crawler_role.role_arn,
            description="Crawls the ticket data from S3 to populate the raw database",
            database_name=self.raw_data_database_name,
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[
                    glue.CfnCrawler.S3TargetProperty(
                        path=f"s3://{self.athena_data_lake_bucket.bucket_name}/{self.raw_data_s3_prefix}/ticket/"
                    )
                ]
            ),
            table_prefix="raw_",
            classifiers=[self.csv_classifier.ref],
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                update_behavior="UPDATE_IN_DATABASE",
                delete_behavior="LOG"
            )
        )

        # 출력값
        cdk.CfnOutput(
            self, "TicketCrawlerName",
            value=self.ticket_crawler.ref,
            export_name=f"{self.stack_name}-TicketCrawlerName"
        )
        
        cdk.CfnOutput(
            self, "CSVClassifierName",
            value=self.csv_classifier.ref,
            export_name=f"{self.stack_name}-CSVClassifierName"
        )
