#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import json
import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_redshiftserverless,
  aws_secretsmanager
)
from constructs import Construct


class RedshiftServerlessStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    rs_admin_user_secret = aws_secretsmanager.Secret(self, 'RedshiftAdminUserSecret',
      generate_secret_string=aws_secretsmanager.SecretStringGenerator(
        secret_string_template=json.dumps({"admin_username": "admin"}),
        generate_string_key="admin_user_password",
        exclude_punctuation=True,
        password_length=8
      )
    )

    redshift_settings = self.node.try_get_context('redshift')
    REDSHIFT_NAMESPACE_NAME = redshift_settings.get('namespace', 'rss-demo-ns')
    REDSHIFT_WORKGROUP_NAME = redshift_settings.get('workgroup', 'rss-demo-wg')

    sg_rs_client = aws_ec2.SecurityGroup(self, 'RedshiftClientSG',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for redshift client',
      security_group_name=f'redshift-client-{REDSHIFT_NAMESPACE_NAME}-sg'
    )
    cdk.Tags.of(sg_rs_client).add('Name', 'redshift-client-sg')

    sg_rs_cluster = aws_ec2.SecurityGroup(self, 'RedshiftClusterSG',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for redshift cluster nodes',
      security_group_name=f'redshift-cluster-{REDSHIFT_NAMESPACE_NAME}-sg'
    )
    sg_rs_cluster.add_ingress_rule(peer=sg_rs_client, connection=aws_ec2.Port.tcp(5439),
      description='redshift-client-sg')
    sg_rs_cluster.add_ingress_rule(peer=sg_rs_cluster, connection=aws_ec2.Port.all_tcp(),
      description='redshift-cluster-sg')
    cdk.Tags.of(sg_rs_cluster).add('Name', 'redshift-cluster-sg')

    self.rss_namespace = aws_redshiftserverless.CfnNamespace(self, 'RedshiftServerlessCfnNamespace',
      namespace_name=REDSHIFT_NAMESPACE_NAME,
      admin_username=rs_admin_user_secret.secret_value_from_json("admin_username").unsafe_unwrap(),
      admin_user_password=rs_admin_user_secret.secret_value_from_json("admin_user_password").unsafe_unwrap(),
      log_exports=['userlog', 'connectionlog', 'useractivitylog'],
    )

    self.rss_workgroup = aws_redshiftserverless.CfnWorkgroup(self, 'RedshiftServerlessCfnWorkgroup',
      workgroup_name=REDSHIFT_WORKGROUP_NAME,
      base_capacity=128,
      config_parameters=[aws_redshiftserverless.CfnWorkgroup.ConfigParameterProperty(
        parameter_key="enable_case_sensitive_identifier",
        parameter_value="true"
      )],
      enhanced_vpc_routing=True,
      namespace_name=self.rss_namespace.namespace_name,
      publicly_accessible=False,
      security_group_ids=[sg_rs_cluster.security_group_id],
      subnet_ids=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids
    )
    self.rss_workgroup.add_dependency(self.rss_namespace)
    self.rss_workgroup.apply_removal_policy(cdk.RemovalPolicy.DESTROY)


    cdk.CfnOutput(self, 'RedshiftNamespaceName',
      value=self.rss_workgroup.namespace_name,
      export_name=f'{self.stack_name}-NamespaceName')
    cdk.CfnOutput(self, 'RedshiftNamespaceNameArn',
      value=self.rss_namespace.attr_namespace_namespace_arn,
      export_name=f'{self.stack_name}-NamespaceNameArn')
    cdk.CfnOutput(self, 'RedshiftWorkgroupName',
      value=self.rss_workgroup.workgroup_name,
      export_name=f'{self.stack_name}-WorkgroupName')
    cdk.CfnOutput(self, 'RedshiftWorkgroupNameArn',
      value=self.rss_workgroup.attr_workgroup_workgroup_arn,
      export_name=f'{self.stack_name}-WorkgroupNameArn')
