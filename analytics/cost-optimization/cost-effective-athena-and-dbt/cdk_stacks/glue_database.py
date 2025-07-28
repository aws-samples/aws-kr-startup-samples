#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_glue as glue
)
from constructs import Construct


class GlueDatabaseStack(Stack):
    """Glue Database를 생성하는 스택"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Raw Data Database
        self.raw_data_database = glue.CfnDatabase(
            self, "RawDataDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="raw_data",
                description="Raw Data Database"
            )
        )

        # 출력값
        cdk.CfnOutput(
            self, "RawDataDatabaseName",
            value=self.raw_data_database.ref,
            export_name=f"{self.stack_name}-RawDataDatabaseName"
        )
