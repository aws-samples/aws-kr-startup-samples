#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    Tags
)
from constructs import Construct


class VpcStack(Stack):
    """VPC 및 네트워킹 리소스를 생성하는 스택"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC 생성
        self.vpc = ec2.Vpc(
            self, "WorkshopVPC",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=3,
            subnet_configuration=[
                # Private Subnets (10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24)
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                # Public Subnets (10.0.4.0/24, 10.0.5.0/24, 10.0.6.0/24)  
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                )
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
            nat_gateways=1  # 비용 절약을 위해 1개로 변경
        )

        # VPC에 태그 추가
        Tags.of(self.vpc).add("Name", "Workshop VPC")

        # 서브넷에 태그 추가
        for i, subnet in enumerate(self.vpc.private_subnets):
            Tags.of(subnet).add("Name", f"Private Subnet {i+1}")
            
        for i, subnet in enumerate(self.vpc.public_subnets):
            Tags.of(subnet).add("Name", f"Public Subnet {i+1}")

        # S3 VPC Endpoint 생성 (Gateway 타입)
        self.s3_vpc_endpoint = ec2.GatewayVpcEndpoint(
            self, "S3VPCEndpoint",
            vpc=self.vpc,
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )]
        )

        # 출력값 정의
        cdk.CfnOutput(
            self, "VpcId",
            value=self.vpc.vpc_id,
            export_name="VpcId"
        )
        
        cdk.CfnOutput(
            self, "PrivateSubnetIds",
            value=",".join([subnet.subnet_id for subnet in self.vpc.private_subnets]),
            export_name="PrivateSubnetIds"
        )
        
        cdk.CfnOutput(
            self, "PublicSubnetIds", 
            value=",".join([subnet.subnet_id for subnet in self.vpc.public_subnets]),
            export_name="PublicSubnetIds"
        )
