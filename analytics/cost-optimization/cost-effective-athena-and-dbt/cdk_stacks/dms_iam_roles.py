#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_iam as iam
)
from constructs import Construct


class DmsIAMRolesStack(Stack):
    """DMS에 필요한 IAM Role들을 생성하는 스택"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DMS VPC Role
        self.dms_vpc_role = iam.Role(
            self, 'DMSVpcRole',
            role_name='dms-vpc-role',
            assumed_by=iam.ServicePrincipal('dms.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonDMSVPCManagementRole'),
            ]
        )

        # DMS CloudWatch Logs Role
        self.dms_cloudwatch_logs_role = iam.Role(
            self, 'DMSCloudWatchLogsRole',
            role_name='dms-cloudwatch-logs-role',
            assumed_by=iam.ServicePrincipal('dms.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonDMSCloudWatchLogsRole'),
            ]
        )

        # 출력값
        cdk.CfnOutput(
            self, 'DMSVpcRoleArn',
            value=self.dms_vpc_role.role_arn,
            export_name=f'{self.stack_name}-DMSVpcRoleArn'
        )
        
        cdk.CfnOutput(
            self, 'DMSCloudWatchLogsRoleArn',
            value=self.dms_cloudwatch_logs_role.role_arn,
            export_name=f'{self.stack_name}-DMSCloudWatchLogsRoleArn'
        )
