#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import re

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_iam,
  aws_s3 as s3,
  aws_kinesisfirehose
)
from constructs import Construct


class KinesisFirehoseStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, kinesis_stream_arn, ops_domain_arn, ops_client_sg_id, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    #XXX: OpenSearch Index naming restrictions
    # https://opensearch.org/docs/2.4/api-reference/index-apis/create-index/#index-naming-restrictions
    OPENSEARCH_INDEX_NAME = self.node.try_get_context('opensearch_index_name')
    assert re.fullmatch(r'[a-z][a-z0-9\-_]+', OPENSEARCH_INDEX_NAME), 'Invalid domain name'

    s3_bucket = s3.Bucket(self, "s3bucket",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: Default: core.RemovalPolicy.RETAIN - The bucket will be orphaned
      bucket_name="firehose-to-ops-{region}-{suffix}".format(
        region=cdk.Aws.REGION, suffix=cdk.Aws.ACCOUNT_ID))

    firehose_role_policy_doc = aws_iam.PolicyDocument()
    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": [s3_bucket.bucket_arn, "{}/*".format(s3_bucket.bucket_arn)],
      "actions": ["s3:AbortMultipartUpload",
        "s3:GetBucketLocation",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads",
        "s3:PutObject"]
    }))

    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["ec2:DescribeVpcs",
        "ec2:DescribeVpcAttribute",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeNetworkInterfaces",
        "ec2:CreateNetworkInterface",
        "ec2:CreateNetworkInterfacePermission",
        "ec2:DeleteNetworkInterface"]
    ))

    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=[ops_domain_arn, "{}/*".format(ops_domain_arn)],
      actions=["es:DescribeElasticsearchDomain",
        "es:DescribeElasticsearchDomains",
        "es:DescribeElasticsearchDomainConfig",
        "es:ESHttpPost",
        "es:ESHttpPut"]
    ))

    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      #XXX: https://aws.amazon.com/premiumsupport/knowledge-center/kinesis-data-firehose-delivery-failure/
      resources=[
        ops_domain_arn,
        f"{ops_domain_arn}/_all/_settings",
        f"{ops_domain_arn}/_cluster/stats",
        f"{ops_domain_arn}/{OPENSEARCH_INDEX_NAME}*/_mapping/%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%",
        f"{ops_domain_arn}/_nodes",
        f"{ops_domain_arn}/_nodes/stats",
        f"{ops_domain_arn}/_nodes/*/stats",
        f"{ops_domain_arn}/_stats",
        f"{ops_domain_arn}/{OPENSEARCH_INDEX_NAME}*/_stats"
      ],
      actions=["es:ESHttpGet"]
    ))

    firehose_log_group_name = f"/aws/kinesisfirehose/{OPENSEARCH_INDEX_NAME}"
    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      #XXX: The ARN will be formatted as follows:
      # arn:{partition}:{service}:{region}:{account}:{resource}{sep}}{resource-name}
      resources=[self.format_arn(service="logs", resource="log-group",
        resource_name="{}:log-stream:*".format(firehose_log_group_name), arn_format=cdk.ArnFormat.COLON_RESOURCE_NAME)],
      actions=["logs:PutLogEvents"]
    ))

    firehose_role = aws_iam.Role(self, "KinesisFirehoseServiceRole",
      role_name=f"KinesisFirehoseServiceRole-{OPENSEARCH_INDEX_NAME}-{cdk.Aws.REGION}",
      assumed_by=aws_iam.ServicePrincipal("firehose.amazonaws.com"),
      #XXX: use inline_policies to work around https://github.com/aws/aws-cdk/issues/5221
      inline_policies={
        "firehose_role_policy": firehose_role_policy_doc
      },
      managed_policies=[
        aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonKinesisReadOnlyAccess'),
      ]
    )

    opensearch_dest_vpc_config = aws_kinesisfirehose.CfnDeliveryStream.VpcConfigurationProperty(
      role_arn=firehose_role.role_arn,
      security_group_ids=[ops_client_sg_id],
      subnet_ids=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids
    )

    opensearch_dest_config = aws_kinesisfirehose.CfnDeliveryStream.AmazonopensearchserviceDestinationConfigurationProperty(
      index_name=OPENSEARCH_INDEX_NAME,
      role_arn=firehose_role.role_arn,
      s3_configuration={
        "bucketArn": s3_bucket.bucket_arn,
        "roleArn": firehose_role.role_arn,

        # the properties below are optional
        "bufferingHints": {
          "intervalInSeconds": 60,
          "sizeInMBs": 1
        },
        "cloudWatchLoggingOptions": {
          "enabled": True,
          "logGroupName": firehose_log_group_name,
          "logStreamName": "S3Backup"
        },
        "compressionFormat": "UNCOMPRESSED", # [GZIP | HADOOP_SNAPPY | Snappy | UNCOMPRESSED | ZIP]
        # Kinesis Data Firehose automatically appends the “YYYY/MM/dd/HH/” UTC prefix to delivered S3 files. You can also specify
        # an extra prefix in front of the time format and add "/" to the end to have it appear as a folder in the S3 console.
        "errorOutputPrefix": "error/",
        "prefix": f"{OPENSEARCH_INDEX_NAME}/"
      },

      # the properties below are optional
      buffering_hints={
        "intervalInSeconds": 60,
        "sizeInMBs": 1
      },
      cloud_watch_logging_options={
        "enabled": True,
        "logGroupName": firehose_log_group_name,
        "logStreamName": "ElasticsearchDelivery"
      },
      domain_arn=ops_domain_arn,
      index_rotation_period="NoRotation", # [NoRotation | OneDay | OneHour | OneMonth | OneWeek]
      retry_options={
        "durationInSeconds": 60
      },
      s3_backup_mode="AllDocuments", # [AllDocuments | FailedDocumentsOnly]
      vpc_configuration=opensearch_dest_vpc_config
    )

    firehose_to_ops_delivery_stream = aws_kinesisfirehose.CfnDeliveryStream(self, "KinesisFirehoseToOPS",
      delivery_stream_name=OPENSEARCH_INDEX_NAME,
      delivery_stream_type="KinesisStreamAsSource",
      kinesis_stream_source_configuration=aws_kinesisfirehose.CfnDeliveryStream.KinesisStreamSourceConfigurationProperty(
        kinesis_stream_arn=kinesis_stream_arn,
        role_arn=firehose_role.role_arn
      ),
      amazonopensearchservice_destination_configuration=opensearch_dest_config,
      tags=[{"key": "Name", "value": OPENSEARCH_INDEX_NAME}]
    )

    cdk.CfnOutput(self, 'FirehoseS3DestBucket', value=s3_bucket.bucket_name, export_name=f'{self.stack_name}-S3DestBucket')
    cdk.CfnOutput(self, 'FirehoseRoleArn', value=firehose_role.role_arn, export_name=f'{self.stack_name}-FirehoseRoleArn')

