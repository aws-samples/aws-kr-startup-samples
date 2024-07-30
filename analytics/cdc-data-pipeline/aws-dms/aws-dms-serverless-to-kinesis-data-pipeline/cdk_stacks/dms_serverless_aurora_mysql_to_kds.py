#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_dms,
  aws_iam,
  aws_secretsmanager
)

from constructs import Construct


class DMSServerlessAuroraMysqlToKinesisStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
              vpc, db_client_sg, db_secret, source_database_hostname, target_kinesis_stream_arn,
              **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    db_cluster_name = self.node.try_get_context('db_cluster_name')
    dms_data_source = self.node.try_get_context('dms_data_source')
    database_name = dms_data_source['database_name']
    table_name = dms_data_source['table_name']

    dms_replication_subnet_group = aws_dms.CfnReplicationSubnetGroup(self, 'DMSReplicationSubnetGroup',
      replication_subnet_group_description='DMS Replication Subnet Group',
      subnet_ids=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids
    )

    source_endpoint_id = db_cluster_name
    dms_source_endpoint = aws_dms.CfnEndpoint(self, 'DMSSourceEndpoint',
      endpoint_identifier=source_endpoint_id,
      endpoint_type='source',
      engine_name='mysql',
      server_name=source_database_hostname,
      port=3306,
      database_name=database_name,
      username=db_secret.secret_value_from_json("username").unsafe_unwrap(),
      password=db_secret.secret_value_from_json("password").unsafe_unwrap()
    )

    dms_kinesis_access_role_policy_doc = aws_iam.PolicyDocument()
    dms_kinesis_access_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "kinesis:DescribeStream",
        "kinesis:PutRecord",
        "kinesis:PutRecords"]
    }))

    dms_target_kinesis_access_role = aws_iam.Role(self, 'DMSTargetKinesisAccessRole',
      role_name='DMSTargetKinesisAccessRole',
      assumed_by=aws_iam.ServicePrincipal('dms.amazonaws.com'),
      inline_policies={
        'KinesisAccessRole': dms_kinesis_access_role_policy_doc
      }
    )

    target_endpoint_id = f"{source_endpoint_id}-cdc-to-kinesis"
    dms_target_endpoint = aws_dms.CfnEndpoint(self, 'DMSTargetEndpoint',
      endpoint_identifier=target_endpoint_id,
      endpoint_type='target',
      engine_name='kinesis',
      kinesis_settings=aws_dms.CfnEndpoint.KinesisSettingsProperty(
        # MessageFormat
        #  L json-unformatted: a single line JSON string with new line format
        #  L json: an attribute-value pair in JSON format
        # Link: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-dms-endpoint-kinesissettings.html
        message_format="json-unformatted",
        service_access_role_arn=dms_target_kinesis_access_role.role_arn,
        stream_arn=target_kinesis_stream_arn
      )
    )

    table_mappings_json = {
      "rules": [
        {
          "rule-type": "selection",
          "rule-id": "1",
          "rule-name": "1",
          "object-locator": {
            "schema-name": database_name,
            "table-name": table_name
          },
          "rule-action": "include",
          "filters": []
        },
        {
          "rule-type": "object-mapping",
          "rule-id": "2",
          "rule-name": "DefaultMapToKinesis",
          "rule-action": "map-record-to-record",
          "object-locator": {
            "schema-name": database_name,
            "table-name": table_name
          }
        }
      ]
    }

    #XXX: AWS DMS - Using Amazon Kinesis Data Streams as a target for AWS Database Migration Service
    # https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.Kinesis.html
    task_settings_json = {
      # Multithreaded full load task settings
      "FullLoadSettings": {
        "MaxFullLoadSubTasks": 8,
      },
      "TargetMetadata": {
        # Multithreaded full load task settings
        "ParallelLoadQueuesPerThread": 0,
        "ParallelLoadThreads": 0,
        "ParallelLoadBufferSize": 0,

        # Multithreaded CDC load task settings
        "ParallelApplyBufferSize": 1000,
        "ParallelApplyQueuesPerThread": 16,
        "ParallelApplyThreads": 8,
      }
    }

    #XXX: For more information, see
    # https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Serverless.Components.html#CHAP_Serverless.create
    dms_replication_config = aws_dms.CfnReplicationConfig(self, 'DMSReplicationConfig',
      compute_config=aws_dms.CfnReplicationConfig.ComputeConfigProperty(
        max_capacity_units=16,
        # min_capacity_units=1, # default: 1 DCU
        multi_az=False,
        preferred_maintenance_window='sat:03:17-sat:03:47',
        replication_subnet_group_id=dms_replication_subnet_group.ref,
        vpc_security_group_ids=[db_client_sg.security_group_id]
      ),
      replication_config_identifier='CDC-MySQLToKinesisTask',
      replication_settings=task_settings_json,
      replication_type='cdc', # [ full-load | cdc | full-load-and-cdc ]
      source_endpoint_arn=dms_source_endpoint.ref,
      table_mappings=table_mappings_json,
      target_endpoint_arn=dms_target_endpoint.ref
    )


    cdk.CfnOutput(self, 'DMSReplicationConfigArn',
      value=dms_replication_config.ref,
      export_name=f'{self.stack_name}-DMSReplicationConfigArn')
    cdk.CfnOutput(self, 'DMSReplicationConfigId',
      value=dms_replication_config.replication_config_identifier,
      export_name=f'{self.stack_name}-DMSReplicationConfigId')
    cdk.CfnOutput(self, 'DMSSourceEndpointId',
      value=dms_source_endpoint.endpoint_identifier,
      export_name=f'{self.stack_name}-DMSSourceEndpointId')
    cdk.CfnOutput(self, 'DMSTargetEndpointId',
      value=dms_target_endpoint.endpoint_identifier,
      export_name=f'{self.stack_name}-DMSTargetEndpointId')
