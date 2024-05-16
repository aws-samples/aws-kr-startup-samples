#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import json
import random
import re
import string

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_opensearchservice,
  aws_secretsmanager
)
from constructs import Construct

random.seed(47)


class OpenSearchStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    #XXX: Amazon OpenSearch Service Domain naming restrictions
    # https://docs.aws.amazon.com/opensearch-service/latest/developerguide/createupdatedomains.html#createdomains
    OPENSEARCH_DEFAULT_DOMAIN_NAME = 'opensearch-{}'.format(''.join(random.sample((string.ascii_letters), k=5)))
    opensearch_domain_name = self.node.try_get_context('opensearch_domain_name') or OPENSEARCH_DEFAULT_DOMAIN_NAME
    assert re.fullmatch(r'([a-z][a-z0-9\-]+){3,28}?', opensearch_domain_name), 'Invalid domain name'

    master_user_secret = aws_secretsmanager.Secret(self, "OpenSearchMasterUserSecret",
      generate_secret_string=aws_secretsmanager.SecretStringGenerator(
        secret_string_template=json.dumps({"username": "admin"}),
        generate_string_key="password",
        # Master password must be at least 8 characters long and contain at least one uppercase letter,
        # one lowercase letter, one number, and one special character.
        password_length=8
      )
    )

    #XXX: aws cdk elastsearch example - https://github.com/aws/aws-cdk/issues/2873
    # You should camelCase the property names instead of PascalCase
    opensearch_domain = aws_opensearchservice.Domain(self, "OpenSearch",
      domain_name=opensearch_domain_name,
      #XXX: Supported versions of OpenSearch and Elasticsearch
      # https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html#choosing-version
      version=aws_opensearchservice.EngineVersion.OPENSEARCH_2_11,
      #XXX: You cannot use graviton instances with non-graviton instances.
      # Use graviton instances as data nodes or use non-graviton instances as master nodes.
      #XXX: Amazon OpenSearch Service - Current generation instance types
      # https://docs.aws.amazon.com/opensearch-service/latest/developerguide/supported-instance-types.html#latest-gen
      # - The OR1 instance types require OpenSearch 2.11 or later.
      # - OR1 instances are only compatible with other Graviton instance types master nodes (C6g, M6g, R6g)
      capacity={
        "master_nodes": 3,
        "master_node_instance_type": "m6g.large.search",
        "data_nodes": 3,
        "data_node_instance_type": "or1.large.search"
      },
      ebs={
        # Volume size must be between 20 and 1536 for or1.large.search instance type and version OpenSearch_2.11
        "volume_size": 20,
        "volume_type": aws_ec2.EbsDeviceVolumeType.GP3
      },
      #XXX: az_count must be equal to vpc subnets count.
      zone_awareness={
        "availability_zone_count": 3
      },
      logging={
        "slow_search_log_enabled": True,
        "app_log_enabled": True,
        "slow_index_log_enabled": True
      },
      fine_grained_access_control=aws_opensearchservice.AdvancedSecurityOptions(
        master_user_name=master_user_secret.secret_value_from_json("username").unsafe_unwrap(),
        master_user_password=master_user_secret.secret_value_from_json("password")
      ),
      # Enforce HTTPS is required when fine-grained access control is enabled.
      enforce_https=True,
      # Node-to-node encryption is required when fine-grained access control is enabled
      node_to_node_encryption=True,
      # Encryption-at-rest is required when fine-grained access control is enabled.
      encryption_at_rest={
        "enabled": True
      },
      use_unsigned_basic_auth=True,
      removal_policy=cdk.RemovalPolicy.DESTROY # default: cdk.RemovalPolicy.RETAIN
    )
    cdk.Tags.of(opensearch_domain).add('Name', opensearch_domain_name)


    cdk.CfnOutput(self, 'OpenSourceDomainArn',
                  value=opensearch_domain.domain_arn,
                  export_name='OpenSourceDomainArn')
    cdk.CfnOutput(self, 'OpenSearchDomainEndpoint',
                  value=f"https://{opensearch_domain.domain_endpoint}",
                  export_name='OpenSearchDomainEndpoint')
    cdk.CfnOutput(self, 'OpenSearchDashboardsURL',
                  value=f"https://{opensearch_domain.domain_endpoint}/_dashboards/",
                  export_name='OpenSearchDashboardsURL')
    cdk.CfnOutput(self, 'OpenSearchSecret', value=master_user_secret.secret_name,
                  export_name='MasterUserSecretId')
