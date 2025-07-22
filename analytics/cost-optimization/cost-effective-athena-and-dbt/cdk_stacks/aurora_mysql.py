#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2,
    aws_logs,
    aws_rds,
    aws_secretsmanager,
    Tags
)
from constructs import Construct


class AuroraMysqlStack(Stack):
    """Aurora MySQL 클러스터를 생성하는 스택"""

    def __init__(self, scope: Construct, construct_id: str, vpc: aws_ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # MySQL 클라이언트 보안 그룹
        self.sg_mysql_client = aws_ec2.SecurityGroup(
            self, 'MySQLClientSG',
            vpc=vpc,
            allow_all_outbound=True,
            description='security group for mysql client',
            security_group_name='dbt-athena-mysql-client-sg'
        )
        Tags.of(self.sg_mysql_client).add('Name', 'mysql-client-sg')

        # MySQL 서버 보안 그룹
        sg_mysql_server = aws_ec2.SecurityGroup(
            self, 'MySQLServerSG',
            vpc=vpc,
            allow_all_outbound=True,
            description='security group for mysql server',
            security_group_name='dbt-athena-mysql-server-sg'
        )
        sg_mysql_server.add_ingress_rule(
            peer=self.sg_mysql_client,
            connection=aws_ec2.Port.tcp(3306),
            description='mysql-client-sg'
        )
        sg_mysql_server.add_ingress_rule(
            peer=sg_mysql_server,
            connection=aws_ec2.Port.all_tcp(),
            description='mysql-server-sg'
        )
        Tags.of(sg_mysql_server).add('Name', 'mysql-server-sg')

        # RDS 서브넷 그룹
        rds_subnet_group = aws_rds.SubnetGroup(
            self, 'MySQLSubnetGroup',
            description='subnet group for mysql',
            subnet_group_name='aurora-mysql',
            vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS),
            vpc=vpc
        )

        # RDS 엔진 정의 (최신 안정 버전 사용)
        rds_engine = aws_rds.DatabaseClusterEngine.aurora_mysql(
            version=aws_rds.AuroraMysqlEngineVersion.VER_3_07_1
        )

        # Aurora 클러스터 파라미터 그룹
        rds_cluster_param_group = aws_rds.ParameterGroup(
            self, 'AuroraMySQLClusterParamGroup',
            engine=rds_engine,
            description='Custom cluster parameter group for aurora-mysql',
            parameters={
                'slow_query_log': '1',
                'wait_timeout': '300',
                'character-set-client-handshake': '0',
                'character_set_server': 'utf8mb4',
                'collation_server': 'utf8mb4_unicode_ci',
                'init_connect': 'SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci',
                'binlog_format': 'ROW'
            }
        )

        # Aurora DB 파라미터 그룹
        rds_db_param_group = aws_rds.ParameterGroup(
            self, 'AuroraMySQLDBParamGroup',
            engine=rds_engine,
            description='Custom parameter group for aurora-mysql instances',
            parameters={
                'slow_query_log': '1',
                'wait_timeout': '300',
                'init_connect': 'SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci'
            }
        )

        # Database Secret (보안 강화)
        db_secret = aws_secretsmanager.Secret(
            self, 'DatabaseSecret',
            generate_secret_string=aws_secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "admin"}),
                generate_string_key="password",
                exclude_punctuation=True,
                password_length=16
            )
        )
        rds_credentials = aws_rds.Credentials.from_secret(db_secret)

        # Aurora 클러스터
        db_cluster = aws_rds.DatabaseCluster(
            self, 'Database',
            engine=rds_engine,
            credentials=rds_credentials,
            writer=aws_rds.ClusterInstance.provisioned(
                "writer",
                instance_type=aws_ec2.InstanceType.of(
                    aws_ec2.InstanceClass.BURSTABLE3, 
                    aws_ec2.InstanceSize.MEDIUM
                ),
                parameter_group=rds_db_param_group,
                auto_minor_version_upgrade=False
            ),
            readers=[
                aws_rds.ClusterInstance.provisioned(
                    "reader",
                    instance_type=aws_ec2.InstanceType.of(
                        aws_ec2.InstanceClass.BURSTABLE3, 
                        aws_ec2.InstanceSize.MEDIUM
                    ),
                    parameter_group=rds_db_param_group,
                    auto_minor_version_upgrade=False
                )
            ],
            parameter_group=rds_cluster_param_group,
            cloudwatch_logs_retention=aws_logs.RetentionDays.THREE_DAYS,
            cluster_identifier="dbt-athena-aurora-cluster",
            subnet_group=rds_subnet_group,
            backup=aws_rds.BackupProps(
                retention=cdk.Duration.days(7),
                preferred_window="03:00-04:00"
            ),
            security_groups=[sg_mysql_server],
            vpc=vpc,
            vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS)
        )

        # 속성으로 저장
        self.db_hostname = db_cluster.cluster_endpoint.hostname
        self.db_secret = db_cluster.secret

        # 출력값
        cdk.CfnOutput(
            self, 'DBClusterEndpointHostName',
            value=self.db_hostname,
            export_name=f'{self.stack_name}-DBClusterEndpointHostName'
        )
        cdk.CfnOutput(
            self, 'DBClusterEndpoint',
            value=db_cluster.cluster_endpoint.socket_address,
            export_name=f'{self.stack_name}-DBClusterEndpoint'
        )
        cdk.CfnOutput(
            self, 'DBClusterReadEndpoint',
            value=db_cluster.cluster_read_endpoint.socket_address,
            export_name=f'{self.stack_name}-DBClusterReadEndpoint'
        )
        cdk.CfnOutput(
            self, 'DBSecretName',
            value=db_cluster.secret.secret_name,
            export_name=f'{self.stack_name}-DBSecretName'
        )
