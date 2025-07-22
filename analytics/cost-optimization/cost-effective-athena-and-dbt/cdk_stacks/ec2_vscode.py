#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    CfnParameter,
    CfnOutput
)
from constructs import Construct
import random
import string


class EC2VSCodeStack(Stack):
    """보안이 강화된 VS Code Server 스택 (CloudFront + HTTPS)"""

    def __init__(self, scope: Construct, construct_id: str,
                 vpc: ec2.Vpc,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.vpc = vpc

        # 랜덤 패스워드 생성 함수 (특수문자 제한)
        def generate_random_password(length=12):
            chars = string.ascii_letters + string.digits
            return ''.join(random.choice(chars) for _ in range(length))

        # 파라미터: VS Code Server 패스워드 (랜덤 생성 + 콘솔에서 확인 가능)
        self.vscode_password = CfnParameter(
            self, "VSCodeServerPassword",
            type="String",
            description="The password for the VS Code server (randomly generated)",
            # no_echo 제거하여 콘솔에서 확인 가능
            default=generate_random_password()
        )

        # 보안 그룹 (포트 8080: dbt docs, 8081: VS Code)
        self.instance_security_group = ec2.SecurityGroup(
            self, "VSCodeServerSecurityGroup",
            vpc=self.vpc,
            description="Allow dbt docs and VS Code server access",
            allow_all_outbound=True
        )

        # dbt docs serve 포트 (8080)
        self.instance_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(8080),
            description="dbt docs serve"
        )

        # VS Code Server 포트 (8081)
        self.instance_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(8081),
            description="VS Code Server"
        )

        # IAM 역할 (최소 권한 원칙)
        self.instance_role = iam.Role(
            self, "VSCodeServerRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
            ],
            inline_policies={
                "S3DataLakeAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:ListBucket",
                                "s3:DeleteObject",
                                "s3:GetBucketLocation"
                            ],
                            resources=[
                                cdk.Fn.import_value("S3Stack:ExportsOutputFnGetAttAthenaDataLakeBucket25753166Arn48064D29"),
                                cdk.Fn.import_value("S3Stack:ExportsOutputFnGetAttAthenaDataLakeBucket25753166Arn48064D29") + "/*"
                            ]
                        )
                    ]
                ),
                "AthenaAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "athena:StartQueryExecution",
                                "athena:GetQueryExecution",
                                "athena:GetQueryResults",
                                "athena:ListQueryExecutions",
                                "athena:GetWorkGroup",
                                "athena:GetDataCatalog"
                            ],
                            resources=["*"]
                        )
                    ]
                ),
                "GlueReadAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "glue:GetDatabase",
                                "glue:GetTable",
                                "glue:GetTables",
                                "glue:GetPartitions"
                            ],
                            resources=["*"]
                        )
                    ]
                )
            }
        )

        # Instance Profile
        self.instance_profile = iam.CfnInstanceProfile(
            self, "VSCodeServerInstanceProfile",
            roles=[self.instance_role.role_name]
        )

        # UserData 스크립트 (Amazon Q 제외)
        user_data_script = f"""#!/bin/bash

echo "####################################################################################################"
echo "Trying to install utilities"
dnf update -y && rm -rf /var/lib/rpm/.rpm.lock
dnf install -y docker git pip && systemctl start docker && chmod 777 /var/run/docker.sock

echo "####################################################################################################"
echo "Trying to install nodejs"
dnf update -y && rm -rf /var/lib/rpm/.rpm.lock
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash - && rm -rf /var/lib/rpm/.rpm.lock && dnf install nodejs -y

echo "####################################################################################################"
echo "Trying to install code-server"
dnf update -y && rm -rf /var/lib/rpm/.rpm.lock
curl -fsSL https://code-server.dev/install.sh | sudo bash - 

echo "####################################################################################################"
echo "Install code-server configuration"
mkdir -p /home/ec2-user/.config/code-server
chown -R ec2-user:ec2-user /home/ec2-user/.config
echo "bind-addr: 0.0.0.0:8081" > /home/ec2-user/.config/code-server/config.yaml
echo "auth: password" >> /home/ec2-user/.config/code-server/config.yaml
echo "password: {self.vscode_password.value_as_string}" >> /home/ec2-user/.config/code-server/config.yaml
echo "cert: false" >> /home/ec2-user/.config/code-server/config.yaml

# VS Code Server 시작 (포트 8081)
su - ec2-user -c 'nohup code-server > /home/ec2-user/code-server.log 2>&1 &'

echo "####################################################################################################"
echo "Install Python and dbt"
dnf install -y python3 python3-pip
pip3 install dbt-core dbt-athena-community

echo "####################################################################################################"
echo "Create workshop environment directory and set environment variables"
mkdir -p /home/ec2-user/environment
chown -R ec2-user:ec2-user /home/ec2-user/environment

# AWS 환경변수 설정
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)

echo "####################################################################################################"
echo "Trying to configure shell environment"
echo "alias ll='ls -la'" >> /home/ec2-user/.bash_profile
echo "alias h='history'" >> /home/ec2-user/.bash_profile
echo "alias rm='rm -i'" >> /home/ec2-user/.bash_profile
echo "export PATH=$PATH:/home/ec2-user/.local/bin" >> /home/ec2-user/.bash_profile
echo "export ACCOUNT_ID=$ACCOUNT_ID" >> /home/ec2-user/.bash_profile
echo "export AWS_DEFAULT_REGION=$REGION" >> /home/ec2-user/.bash_profile
echo "export AWS_REGION=$REGION" >> /home/ec2-user/.bash_profile
"""

        # EC2 인스턴스
        self.instance = ec2.Instance(
            self, "VSCodeServerInstance",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.LARGE
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            security_group=self.instance_security_group,
            role=self.instance_role,
            user_data=ec2.UserData.custom(user_data_script),
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=100,
                        volume_type=ec2.EbsDeviceVolumeType.GP3
                    )
                )
            ]
        )

        # CloudFront Distribution (VS Code용 - 포트 8081)
        self.cloudfront_distribution = cloudfront.Distribution(
            self, "CloudFrontDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    self.instance.instance_public_dns_name,
                    http_port=8081,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER
            ),
            comment="VSCode Server Distribution"
        )

        # 출력값
        CfnOutput(
            self, "VSCodeServerURL",
            description="URL to access the VS Code server via CloudFront (HTTPS)",
            value=f"https://{self.cloudfront_distribution.distribution_domain_name}"
        )

        CfnOutput(
            self, "VSCodeServerDirectURL",
            description="Direct URL to access the VS Code server (HTTP)",
            value=f"http://{self.instance.instance_public_dns_name}:8081"
        )

        CfnOutput(
            self, "VSCodePassword",
            description="VS Code Server Password (also available in Parameters tab)",
            value=self.vscode_password.value_as_string
        )

        CfnOutput(
            self, "DBTDocsURL",
            description="URL for dbt docs serve (run manually: dbt docs serve)",
            value=f"http://{self.instance.instance_public_dns_name}:8080"
        )

        CfnOutput(
            self, "InstanceId",
            description="EC2 Instance ID for VS Code Server",
            value=self.instance.instance_id
        )
