#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_iam,
  aws_s3 as s3,
  aws_kinesisfirehose
)
from constructs import Construct


from aws_cdk.aws_kinesisfirehose import CfnDeliveryStream as firehose_cfn

class KinesisFirehoseStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    firehose_config = self.node.try_get_context('firehose')

    S3_DEFAULT_BUCKET_NAME = "apigw-access-log-to-firehose-{region}-{account_id}".format(
        region=cdk.Aws.REGION, account_id=cdk.Aws.ACCOUNT_ID)
    s3_bucket_name = firehose_config.get('s3_bucket', S3_DEFAULT_BUCKET_NAME)
    s3_bucket = s3.Bucket(self, "s3bucket",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: Default: core.RemovalPolicy.RETAIN - The bucket will be orphaned
      bucket_name=s3_bucket_name)

    FIREHOSE_STREAM_NAME = f"amazon-apigateway-{firehose_config['stream_name']}"
    FIREHOSE_BUFFER_SIZE = firehose_config['buffer_size_in_mbs']
    FIREHOSE_BUFFER_INTERVAL = firehose_config['buffer_interval_in_seconds']
    FIREHOSE_TO_S3_PREFIX = firehose_config['prefix']
    FIREHOSE_TO_S3_ERROR_OUTPUT_PREFIX = firehose_config['error_output_prefix']
    FIREHOSE_TO_S3_OUTPUT_FOLDER = firehose_config['s3_output_folder']

    assert f'{FIREHOSE_TO_S3_OUTPUT_FOLDER}/' == FIREHOSE_TO_S3_PREFIX[:len(FIREHOSE_TO_S3_OUTPUT_FOLDER) + 1]

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
      resources=["*"],
      actions=["glue:GetTable",
        "glue:GetTableVersion",
        "glue:GetTableVersions"]
    ))

    firehose_log_group_name = f"/aws/kinesisfirehose/{FIREHOSE_STREAM_NAME}"
    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      #XXX: The ARN will be formatted as follows:
      # arn:{partition}:{service}:{region}:{account}:{resource}{sep}}{resource-name}
      resources=[self.format_arn(service="logs", resource="log-group",
        resource_name="{}:log-stream:*".format(firehose_log_group_name),
        arn_format=cdk.ArnFormat.COLON_RESOURCE_NAME)],
      actions=["logs:PutLogEvents"]
    ))

    firehose_role = aws_iam.Role(self, "KinesisFirehoseDeliveryRole",
      role_name="FirehoseRole-{stream_name}-{region}".format(
        stream_name='random-gen', region=cdk.Aws.REGION),
      assumed_by=aws_iam.ServicePrincipal("firehose.amazonaws.com"),
      #XXX: use inline_policies to work around https://github.com/aws/aws-cdk/issues/5221
      inline_policies={
        "firehose_role_policy": firehose_role_policy_doc
      }
    )

    ext_s3_dest_config = firehose_cfn.ExtendedS3DestinationConfigurationProperty(
      bucket_arn=s3_bucket.bucket_arn,
      role_arn=firehose_role.role_arn,
      buffering_hints={
        "intervalInSeconds": FIREHOSE_BUFFER_INTERVAL,
        "sizeInMBs": FIREHOSE_BUFFER_SIZE
      },
      cloud_watch_logging_options={
        "enabled": True,
        "logGroupName": firehose_log_group_name,
        "logStreamName": f"{self.stack_name}-S3Delivery"
      },
      compression_format="UNCOMPRESSED", # [GZIP | HADOOP_SNAPPY | Snappy | UNCOMPRESSED | ZIP]
      data_format_conversion_configuration={
        "enabled": False
      },
      dynamic_partitioning_configuration={
        "enabled": False
      },
      error_output_prefix=FIREHOSE_TO_S3_ERROR_OUTPUT_PREFIX,
      prefix=FIREHOSE_TO_S3_PREFIX
    )

    firehose_to_s3_delivery_stream = aws_kinesisfirehose.CfnDeliveryStream(self, "KinesisFirehoseToS3",
      delivery_stream_name=FIREHOSE_STREAM_NAME,
      delivery_stream_type="DirectPut",
      extended_s3_destination_configuration=ext_s3_dest_config
    )

    self.firehose_arn = firehose_to_s3_delivery_stream.attr_arn
    self.s3_dest_bucket_name = s3_bucket.bucket_name
    self.s3_dest_folder_name = FIREHOSE_TO_S3_OUTPUT_FOLDER

    cdk.CfnOutput(self, '{}_S3DestBucket'.format(self.stack_name), value=s3_bucket.bucket_name, export_name=f'{self.stack_name}-S3DestBucket')
    cdk.CfnOutput(self, 'FirehoseRoleArn', value=firehose_role.role_arn, export_name=f'{self.stack_name}-FirehoseRoleArn')
