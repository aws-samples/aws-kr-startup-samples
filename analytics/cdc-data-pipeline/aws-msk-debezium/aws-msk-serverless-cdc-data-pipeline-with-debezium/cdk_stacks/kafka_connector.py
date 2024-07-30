#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import boto3

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_iam,
  aws_kafkaconnect,
  aws_logs,
)
from constructs import Construct


def get_kafka_booststrap_servers(kafka_cluster_name, region_name):
  client = boto3.client('kafka', region_name=region_name)
  response = client.list_clusters_v2(ClusterNameFilter=kafka_cluster_name)
  cluster_info_list = [e for e in response['ClusterInfoList'] if e['ClusterName'] == kafka_cluster_name]
  if not cluster_info_list:
    kafka_bootstrap_servers = "localhost:9094"
  else:
    msk_cluster_arn = cluster_info_list[0]['ClusterArn']
    msk_brokers = client.get_bootstrap_brokers(ClusterArn=msk_cluster_arn)
    kafka_bootstrap_servers = msk_brokers['BootstrapBrokerStringSaslIam']
    assert kafka_bootstrap_servers

  return kafka_bootstrap_servers


def get_worker_configuration(worker_configuration_name, region_name):
  client = boto3.client('kafkaconnect', region_name=region_name)
  response = client.list_worker_configurations()
  worker_configuration_list = response.get('workerConfigurations', [])
  if not worker_configuration_list:
    ret = {
      'revision': 1,
      'worker_configuration_arn': f"arn:aws:kafkaconnect:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:worker-configuration/{worker_configuration_name}/*"
    }
  else:
    worker_configuration = [e for e in worker_configuration_list if e['name'] == worker_configuration_name][0]
    assert worker_configuration
    ret = {
      'revision': worker_configuration['latestRevision']['revision'],
      'worker_configuration_arn': worker_configuration['workerConfigurationArn']
    }
  return ret


def get_custom_plugin(custom_plugin_name, region_name):
  client = boto3.client('kafkaconnect', region_name=region_name)
  response = client.list_custom_plugins()
  custom_plugin_list = response.get('customPlugins', [])
  if not custom_plugin_list:
    ret = {
      'revision': 1,
      'custom_plugin_arn': f"arn:aws:kafkaconnect:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:custom-plugin/{custom_plugin_name}/*"
    }
  else:
    custom_plugin = [e for e in custom_plugin_list if e['name'] == custom_plugin_name][0]
    assert custom_plugin
    ret = {
      'revision': custom_plugin['latestRevision']['revision'],
      'custom_plugin_arn': custom_plugin['customPluginArn']
    }
  return ret


class KafkaConnectorStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
    vpc, db_hostname, sg_rds_client, rds_credentials,
    msk_cluster_name, msk_cluster_vpc_configs,
    **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    kafka_booststrap_servers = get_kafka_booststrap_servers(msk_cluster_name, vpc.env.region)

    msk_connector_custom_plugin_name = self.node.try_get_context('msk_connector_custom_plugin_name')
    msk_connector_custom_plugin = get_custom_plugin(msk_connector_custom_plugin_name, vpc.env.region)

    msk_connector_worker_configuration_name = self.node.try_get_context('msk_connector_worker_configuration_name')
    msk_connector_worker_configuration = get_worker_configuration(msk_connector_worker_configuration_name, vpc.env.region)

    msk_connector_configuration = self.node.try_get_context('msk_connector_configuration')
    msk_connector_name = self.node.try_get_context('msk_connector_name')

    msk_connector_log_group = aws_logs.LogGroup(self, 'KafkaConnectorLogGroup',
      log_group_name=f'/aws-msk-connector/{msk_cluster_name}',
      retention=aws_logs.RetentionDays.THREE_DAYS,
      removal_policy=cdk.RemovalPolicy.DESTROY
    )

    kafka_cluster_access_policy_doc = aws_iam.PolicyDocument()
    kafka_cluster_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "actions": [
        "kafka-cluster:Connect",
        "kafka-cluster:AlterCluster",
        "kafka-cluster:DescribeCluster"
      ],
      "resources": [ f"arn:aws:kafka:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:cluster/{msk_cluster_name}/*" ]
    }))

    kafka_cluster_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "actions": [
        "kafka-cluster:*Topic*",
        "kafka-cluster:WriteData",
        "kafka-cluster:ReadData"
      ],
      "resources": [ f"arn:aws:kafka:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:topic/{msk_cluster_name}/*" ]
    }))

    kafka_cluster_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "actions": [
        "kafka-cluster:AlterGroup",
        "kafka-cluster:DescribeGroup"
      ],
      "resources": [ f"arn:aws:kafka:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:group/{msk_cluster_name}/*" ],
    }))

    secretmanager_readonly_access_policy_doc = aws_iam.PolicyDocument()
    secretmanager_readonly_access_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "actions": [
        "secretsmanager:GetResourcePolicy",
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:ListSecretVersionIds"
      ],
      "resources": [ rds_credentials.secret_full_arn ]
    }))

    #XXX: For more information, see https://docs.aws.amazon.com/msk/latest/developerguide/create-iam-role.html
    msk_connector_execution_role = aws_iam.Role(self, 'MSKConnectorExecutionRole',
      role_name=f'MSKConnectorExecutionRole-{msk_cluster_name}',
      assumed_by=aws_iam.ServicePrincipal('kafkaconnect.amazonaws.com'),
      path='/',
      inline_policies={
        'KafkaClusterAccessPolicy': kafka_cluster_access_policy_doc,
        'SecretsManagerReadOnlyAccessPolicy': secretmanager_readonly_access_policy_doc
      }
    )

    rds_secret_name = rds_credentials.secret_name

    kafka_connect_vpc_security_group_ids = [sg_rds_client.security_group_id]
    kafka_connect_vpc_subnets = []
    for vpc_config in msk_cluster_vpc_configs:
      kafka_connect_vpc_security_group_ids.extend(vpc_config.security_groups)
      kafka_connect_vpc_subnets.extend(vpc_config.subnet_ids)

    #XXX: For more information about Debezium connector, see the following url:
    # https://docs.aws.amazon.com/msk/latest/developerguide/mkc-debeziumsource-connector-example.html
    msk_connector = aws_kafkaconnect.CfnConnector(self, "KafkaCfnConnector",
      capacity=aws_kafkaconnect.CfnConnector.CapacityProperty(
        auto_scaling=aws_kafkaconnect.CfnConnector.AutoScalingProperty(
          max_worker_count=2,
          mcu_count=1,
          min_worker_count=1,
          scale_in_policy=aws_kafkaconnect.CfnConnector.ScaleInPolicyProperty(
            cpu_utilization_percentage=20
          ),
          scale_out_policy=aws_kafkaconnect.CfnConnector.ScaleOutPolicyProperty(
            cpu_utilization_percentage=80
          )
        )
      ),
      connector_configuration={
        "connector.class": "io.debezium.connector.mysql.MySqlConnector",
        "tasks.max": msk_connector_configuration['tasks.max'],

        "database.hostname": db_hostname,
        "database.port": "3306",
        "database.user": f"${{secretManager:{rds_secret_name}:username}}",
        "database.password": f"${{secretManager:{rds_secret_name}:password}}",
        "database.server.id": "123456", # database.server.id shoud be given
        "database.include.list": msk_connector_configuration['database.include.list'],

        "topic.prefix": msk_connector_configuration['topic.prefix'],
        "topic.creation.enable": "true",
        "topic.creation.default.partitions": msk_connector_configuration['topic.creation.default.partitions'],
        "topic.creation.default.replication.factor": msk_connector_configuration['topic.creation.default.replication.factor'],

        "include.schema.changes": msk_connector_configuration['include.schema.changes'],

        "schema.history.internal.kafka.topic": msk_connector_configuration['schema.history.internal.kafka.topic'],
        "schema.history.internal.kafka.bootstrap.servers": kafka_booststrap_servers,
        "schema.history.internal.consumer.security.protocol": "SASL_SSL",
        "schema.history.internal.consumer.sasl.mechanism": "AWS_MSK_IAM",
        "schema.history.internal.consumer.sasl.jaas.config": "software.amazon.msk.auth.iam.IAMLoginModule required;",
        "schema.history.internal.consumer.sasl.client.callback.handler.class": "software.amazon.msk.auth.iam.IAMClientCallbackHandler",
        "schema.history.internal.producer.security.protocol": "SASL_SSL",
        "schema.history.internal.producer.sasl.mechanism": "AWS_MSK_IAM",
        "schema.history.internal.producer.sasl.jaas.config": "software.amazon.msk.auth.iam.IAMLoginModule required;",
        "schema.history.internal.producer.sasl.client.callback.handler.class": "software.amazon.msk.auth.iam.IAMClientCallbackHandler",
      },
      connector_name=msk_connector_name,
      kafka_cluster=aws_kafkaconnect.CfnConnector.KafkaClusterProperty(
        apache_kafka_cluster=aws_kafkaconnect.CfnConnector.ApacheKafkaClusterProperty(
          bootstrap_servers=kafka_booststrap_servers,
          vpc=aws_kafkaconnect.CfnConnector.VpcProperty(
            security_groups=kafka_connect_vpc_security_group_ids,
            subnets=kafka_connect_vpc_subnets
          )
        )
      ),
      kafka_cluster_client_authentication=aws_kafkaconnect.CfnConnector.KafkaClusterClientAuthenticationProperty(
        authentication_type="IAM"
      ),
      kafka_cluster_encryption_in_transit=aws_kafkaconnect.CfnConnector.KafkaClusterEncryptionInTransitProperty(
        encryption_type="TLS"
      ),
      kafka_connect_version="2.7.1",
      plugins=[aws_kafkaconnect.CfnConnector.PluginProperty(
        custom_plugin=aws_kafkaconnect.CfnConnector.CustomPluginProperty(
          custom_plugin_arn=msk_connector_custom_plugin['custom_plugin_arn'],
          revision=msk_connector_custom_plugin['revision']
        )
      )],
      service_execution_role_arn=msk_connector_execution_role.role_arn,
      log_delivery=aws_kafkaconnect.CfnConnector.LogDeliveryProperty(
        worker_log_delivery=aws_kafkaconnect.CfnConnector.WorkerLogDeliveryProperty(
          cloud_watch_logs=aws_kafkaconnect.CfnConnector.CloudWatchLogsLogDeliveryProperty(
            enabled=True,
            log_group=msk_connector_log_group.log_group_name
          )
        )
      ),
      worker_configuration=aws_kafkaconnect.CfnConnector.WorkerConfigurationProperty(
        revision=msk_connector_worker_configuration['revision'],
        worker_configuration_arn=msk_connector_worker_configuration['worker_configuration_arn']
      )
    )


    cdk.CfnOutput(self, 'MSKConnectServiceExecutionRoleArn', value=msk_connector.service_execution_role_arn,
      export_name=f'{self.stack_name}-ServiceExecutionRoleArn')
    cdk.CfnOutput(self, 'MSKConnectCustomPluginArn', value=msk_connector.plugins[0].custom_plugin.custom_plugin_arn,
      export_name=f'{self.stack_name}-CustomPluginArn')
    cdk.CfnOutput(self, 'MSKConnectWorkConfiguration', value=msk_connector.worker_configuration.worker_configuration_arn,
      export_name=f'{self.stack_name}-WorkConfigurationArn')
