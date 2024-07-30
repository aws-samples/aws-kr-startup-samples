#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_iam,
  aws_kendra
)
from constructs import Construct


class KendraIndexStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    kendra_index_role_policy_doc = aws_iam.PolicyDocument()
    kendra_index_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "conditions": {
        "StringEquals": {
          "cloudwatch:namespace": [
            "Kendra"
          ]
        }
      },
      "actions": ["cloudwatch:PutMetricData"]
    }))

    kendra_index_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "logs:DescribeLogGroups"
      ]
    }))

    kendra_index_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": [f"arn:aws:logs:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:log-group:/aws/kendra/*"],
      "actions": [
        "logs:CreateLogGroup"
      ]
    }))

    kendra_index_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": [f"arn:aws:logs:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:log-group:/aws/kendra/*:log-stream:*"],
      "actions": [
        "logs:DescribeLogStreams",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    }))

    kendra_index_role = aws_iam.Role(self, 'KendraIndexRole',
      role_name=f'{self.stack_name}-DocsKendraIndexRole',
      assumed_by=aws_iam.ServicePrincipal('kendra.amazonaws.com'),
      inline_policies={
        'DocsKendraIndexRolePolicy': kendra_index_role_policy_doc
      }
    )

    kendra_index = aws_kendra.CfnIndex(self, "KendraIndex",
      edition="ENTERPRISE_EDITION", # [DEVELOPER_EDITION, ENTERPRISE_EDITION]
      name=f'{self.stack_name}-Index',
      role_arn=kendra_index_role.role_arn
    )

    self.kendra_index_id = kendra_index.attr_id

    cdk.CfnOutput(self, 'KendraIndexId',
      value=self.kendra_index_id,
      export_name=f"{self.stack_name}-KendraIndexId")
