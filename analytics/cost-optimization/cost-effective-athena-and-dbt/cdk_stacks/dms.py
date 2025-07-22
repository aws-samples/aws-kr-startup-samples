#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_dms as dms,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_s3 as s3
)
from constructs import Construct


class DmsStack(Stack):
    """DMS 리소스들을 생성하는 스택"""

    def __init__(self, scope: Construct, construct_id: str,
                 vpc: ec2.Vpc,
                 mysql_client_sg: ec2.SecurityGroup,
                 db_secret: secretsmanager.Secret,
                 source_database_hostname: str,
                 athena_data_lake_bucket: s3.Bucket,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = vpc
        self.mysql_client_sg = mysql_client_sg
        self.db_secret = db_secret
        self.source_database_hostname = source_database_hostname
        self.athena_data_lake_bucket = athena_data_lake_bucket

        # DMS Replication Subnet Group
        self.dms_replication_subnet_group = dms.CfnReplicationSubnetGroup(
            self, 'DMSReplicationSubnetGroup',
            replication_subnet_group_description='DMS Replication Subnet Group',
            subnet_ids=self.vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ).subnet_ids
        )

        # DMS Source Endpoint (Aurora MySQL)
        source_endpoint_id = "dbt-athena-aurora-cluster"
        self.dms_source_endpoint = dms.CfnEndpoint(
            self, 'DMSSourceEndpoint',
            endpoint_identifier=source_endpoint_id,
            endpoint_type='source',
            engine_name='mysql',
            server_name=self.source_database_hostname,
            port=3306,
            database_name='rds',  # mysql -> rds로 변경
            username=self.db_secret.secret_value_from_json("username").unsafe_unwrap(),
            password=self.db_secret.secret_value_from_json("password").unsafe_unwrap()
        )

        # DMS Target S3 Access Role
        self.dms_target_s3_access_role = iam.Role(
            self, 'DMSTargetS3AccessRole',
            role_name='DMSTargetS3AccessRole',
            assumed_by=iam.ServicePrincipal('dms.amazonaws.com'),
            inline_policies={
                'S3AccessRole': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            resources=["*"],
                            actions=[
                                "s3:PutObject",
                                "s3:DeleteObject", 
                                "s3:PutObjectTagging",
                                "s3:ListBucket"
                            ]
                        )
                    ]
                )
            }
        )

        # DMS Target Endpoint (S3)
        target_endpoint_id = f"{source_endpoint_id}-to-s3"
        self.dms_target_endpoint = dms.CfnEndpoint(
            self, 'DMSTargetEndpoint',
            endpoint_identifier=target_endpoint_id,
            endpoint_type='target',
            engine_name='s3',
            s3_settings=dms.CfnEndpoint.S3SettingsProperty(
                bucket_name=self.athena_data_lake_bucket.bucket_name,
                bucket_folder="raw_data",
                service_access_role_arn=self.dms_target_s3_access_role.role_arn,
                data_format='parquet',
                parquet_version='parquet-2-0',
                parquet_timestamp_in_millisecond=True,
                date_partition_enabled=True,
                date_partition_sequence='YYYYMMDD',
                add_column_name=True
            )
        )

        # Table Mappings (기존 CloudFormation과 동일하게 store_sales 테이블만)
        table_mappings_json = {
            "rules": [
                {
                    "rule-type": "selection",
                    "rule-id": "1",
                    "rule-name": "store_sales",
                    "object-locator": {
                        "schema-name": "%",
                        "table-name": "store_sales"
                    },
                    "rule-action": "include"
                }
            ]
        }

        # Task Settings (기존 CloudFormation과 동일)
        task_settings_json = {
            "TargetMetadata": {
                "BatchApplyEnabled": True
            },
            "FullLoadSettings": {
                "TargetTablePrepMode": "DO_NOTHING",
                "CreatePkAfterFullLoad": False,
                "StopTaskCachedChangesApplied": False,
                "StopTaskCachedChangesNotApplied": False,
                "MaxFullLoadSubTasks": 8,
                "TransactionConsistencyTimeout": 600,
                "CommitRate": 10000
            },
            "Logging": {
                "EnableLogging": True,
                "LogComponents": [
                    {
                        "Id": "SOURCE_UNLOAD",
                        "Severity": "LOGGER_SEVERITY_DEFAULT"
                    },
                    {
                        "Id": "TARGET_LOAD", 
                        "Severity": "LOGGER_SEVERITY_DEFAULT"
                    }
                ]
            }
        }

        # DMS Replication Config (Serverless)
        self.dms_replication_config = dms.CfnReplicationConfig(
            self, 'DMSReplicationConfig',
            compute_config=dms.CfnReplicationConfig.ComputeConfigProperty(
                max_capacity_units=16,
                multi_az=False,
                preferred_maintenance_window='sat:03:17-sat:03:47',
                replication_subnet_group_id=self.dms_replication_subnet_group.ref,
                vpc_security_group_ids=[self.mysql_client_sg.security_group_id]
            ),
            replication_config_identifier='dbt-athena-dms-config',
            replication_type='full-load-and-cdc',
            source_endpoint_arn=self.dms_source_endpoint.ref,
            target_endpoint_arn=self.dms_target_endpoint.ref,
            table_mappings=table_mappings_json,  # JSON 객체로 직접 전달
            replication_settings=task_settings_json  # JSON 객체로 직접 전달
        )

        # 출력값
        cdk.CfnOutput(
            self, 'DMSSourceEndpointArn',
            value=self.dms_source_endpoint.ref,
            export_name=f'{self.stack_name}-DMSSourceEndpointArn'
        )
        
        cdk.CfnOutput(
            self, 'DMSTargetEndpointArn',
            value=self.dms_target_endpoint.ref,
            export_name=f'{self.stack_name}-DMSTargetEndpointArn'
        )
        
        cdk.CfnOutput(
            self, 'DMSReplicationConfigArn',
            value=self.dms_replication_config.ref,
            export_name=f'{self.stack_name}-DMSReplicationConfigArn'
        )
