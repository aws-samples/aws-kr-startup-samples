#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_logs,
  aws_rds
)
from constructs import Construct


class AuroraPostgresqlStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    sg_postgresql_client = aws_ec2.SecurityGroup(self, 'PostgreSQLClientSG',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for postgresql client',
      security_group_name='postgresql-client-sg'
    )
    cdk.Tags.of(sg_postgresql_client).add('Name', 'postgresql-client-sg')

    sg_postgresql_server = aws_ec2.SecurityGroup(self, 'PostgreSQLServerSG',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for postgresql',
      security_group_name='postgresql-server-sg'
    )
    sg_postgresql_server.add_ingress_rule(peer=sg_postgresql_server, connection=aws_ec2.Port.all_tcp(),
      description='postgresql-server-sg')
    sg_postgresql_server.add_ingress_rule(peer=sg_postgresql_client, connection=aws_ec2.Port.tcp(5432),
      description='postgresql-client-sg')
    cdk.Tags.of(sg_postgresql_server).add('Name', 'postgresql-server-sg')

    rds_subnet_group = aws_rds.SubnetGroup(self, 'PostgreSQLSubnetGroup',
      description='subnet group for postgresql',
      subnet_group_name=f'{self.stack_name}-aurora-postgresql',
      vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS),
      vpc=vpc
    )

    db_cluster_name = self.node.try_get_context('db_cluster_name')
    rds_credentials = aws_rds.Credentials.from_generated_secret("postgres")

    AURORA_POSTGRES_ENGINE_VERSION = aws_rds.AuroraPostgresEngineVersion.VER_16_3
    rds_engine = aws_rds.DatabaseClusterEngine.aurora_postgres(version=AURORA_POSTGRES_ENGINE_VERSION)

    #XXX: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.Reference.ParameterGroups.html#AuroraPostgreSQL.Reference.Parameters.Cluster
    rds_cluster_param_group = aws_rds.ParameterGroup(self, 'AuroraPostgreSQLClusterParamGroup',
      engine=rds_engine,
      description=f'Custom cluster parameter group for aurora-postgresql{AURORA_POSTGRES_ENGINE_VERSION.aurora_postgres_major_version}',
      parameters={
        'log_min_duration_statement': '15000', # 15 sec
        'default_transaction_isolation': 'read committed',
        'client_encoding': 'UTF8',
        'rds.allowed_extensions': '*',
        'shared_preload_libraries': 'pg_stat_statements,pg_similarity'
      }
    )

    #XXX: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.Reference.ParameterGroups.html#AuroraPostgreSQL.Reference.Parameters.Instance
    rds_db_param_group = aws_rds.ParameterGroup(self, 'AuroraPostgreSQLDBParamGroup',
      engine=rds_engine,
      description=f'Custom parameter group for aurora-postgresql{AURORA_POSTGRES_ENGINE_VERSION.aurora_postgres_major_version}',
      parameters={
        'log_min_duration_statement': '15000', # 15 sec
        'default_transaction_isolation': 'read committed',
        'rds.allowed_extensions': '*',
        'shared_preload_libraries': 'pg_stat_statements,pg_similarity'
      }
    )

    aurora_vectorstore_database_name = self.node.try_get_context('aurora_vectorstore_database_name') or 'postgres'

    db_cluster = aws_rds.DatabaseCluster(self, 'AuroraPostgresDBCluster',
      engine=rds_engine,
      credentials=rds_credentials, # A username of 'admin' (or 'postgres' for PostgreSQL) and SecretsManager-generated password
      default_database_name=aurora_vectorstore_database_name,
      writer=aws_rds.ClusterInstance.provisioned("Writer",
        instance_type=aws_ec2.InstanceType.of(aws_ec2.InstanceClass.MEMORY6_GRAVITON, aws_ec2.InstanceSize.LARGE),
        parameter_group=rds_db_param_group,
        auto_minor_version_upgrade=False,
      ),
      readers=[
        aws_rds.ClusterInstance.provisioned("Reader",
          instance_type=aws_ec2.InstanceType.of(aws_ec2.InstanceClass.MEMORY6_GRAVITON, aws_ec2.InstanceSize.LARGE),
          parameter_group=rds_db_param_group,
          auto_minor_version_upgrade=False
        )
      ],
      parameter_group=rds_cluster_param_group,
      cloudwatch_logs_retention=aws_logs.RetentionDays.THREE_DAYS,
      cluster_identifier=db_cluster_name,
      subnet_group=rds_subnet_group,
      backup=aws_rds.BackupProps(
        retention=cdk.Duration.days(3),
        preferred_window="03:00-04:00"
      ),
      security_groups=[sg_postgresql_server],
      vpc=vpc,
      vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS)
    )
    db_cluster.apply_removal_policy(cdk.RemovalPolicy.DESTROY) #XXX: For testing

    # Add Data API access to the Aurora cluster
    db_cluster.node.default_child.add_override('Properties.EnableHttpEndpoint', True)


    self.rds_credentials_secret_arn = db_cluster.secret.secret_arn
    self.rds_cluster_arn = db_cluster.cluster_arn
    self.sg_rds_client = sg_postgresql_client


    cdk.CfnOutput(self, 'DBClusterId',
      value=db_cluster.cluster_identifier,
      export_name='VectorDBClusterId')
    cdk.CfnOutput(self, 'DBClusterEndpoint',
      value=db_cluster.cluster_endpoint.socket_address,
      export_name='VectorDBClusterEndpoint')
    cdk.CfnOutput(self, 'DBClusterReadEndpoint',
      value=db_cluster.cluster_read_endpoint.socket_address,
      export_name='VectorDBClusterReadEndpoint')
    #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_secretsmanager/README.html
    # secret_arn="arn:aws:secretsmanager:<region>:<account-id-number>:secret:<secret-name>-<random-6-characters>"
    cdk.CfnOutput(self, 'DBSecret',
      value=db_cluster.secret.secret_name,
      export_name='VectorDBSecret')
    cdk.CfnOutput(self, 'DBClientSecurityGroupId',
      value=sg_postgresql_client.security_group_id,
      export_name='VectorDBClientSecurityGroupId')
    cdk.CfnOutput(self, 'VectorDBName',
      value=aurora_vectorstore_database_name,
      export_name='VectorDBName')
