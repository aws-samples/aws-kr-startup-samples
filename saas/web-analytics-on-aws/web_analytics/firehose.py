#!/usr/bin/env python3
import random
import string

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_iam,
  aws_s3 as s3,
  aws_kinesisfirehose,
)

from constructs import Construct
from aws_cdk.aws_kinesisfirehose import CfnDeliveryStream as cfn

random.seed(31)

class FirehoseStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, source_kinesis_stream_arn, data_transform_lambda_fn, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    s3_bucket = s3.Bucket(self, "s3bucket",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: Default: cdk.RemovalPolicy.RETAIN - The bucket will be orphaned
      bucket_name="web-analytics-{region}-{account_id}".format(
        region=cdk.Aws.REGION, account_id=cdk.Aws.ACCOUNT_ID))

    FIREHOSE_DEFAULT_STREAM_NAME = 'PUT-S3-{}'.format(''.join(random.sample((string.ascii_letters), k=5)))
    firehose_config = self.node.try_get_context('firehose')

    FIREHOSE_STREAM_NAME = firehose_config.get('stream_name', FIREHOSE_DEFAULT_STREAM_NAME)
    FIREHOSE_BUFFER_SIZE = firehose_config['buffer_size_in_mbs']
    FIREHOSE_BUFFER_INTERVAL = firehose_config['buffer_interval_in_seconds']
    FIREHOSE_LAMBDA_BUFFER_SIZE = firehose_config['lambda_buffer_size_in_mbs']
    FIREHOSE_LAMBDA_BUFFER_INTERVAL = firehose_config['lambda_buffer_interval_in_seconds']
    FIREHOSE_LAMBDA_NUMBER_OF_RETRIES = firehose_config['lambda_number_of_retries']
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

    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=[source_kinesis_stream_arn],
      actions=["kinesis:DescribeStream",
        "kinesis:GetShardIterator",
        "kinesis:GetRecords"]
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

    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      #XXX: The ARN will be formatted as follows:
      # arn:{partition}:{service}:{region}:{account}:{resource}{sep}}{resource-name}
      "resources": [self.format_arn(partition="aws", service="lambda",
        region=cdk.Aws.REGION, account=cdk.Aws.ACCOUNT_ID, resource="function",
        resource_name="{}:*".format(data_transform_lambda_fn.function_name),
        arn_format=cdk.ArnFormat.COLON_RESOURCE_NAME)],
      "actions": ["lambda:InvokeFunction",
        "lambda:GetFunctionConfiguration"]
    }))

    firehose_role = aws_iam.Role(self, "KinesisFirehoseDeliveryRole",
      role_name="KinesisFirehoseServiceRole-{stream_name}-{region}".format(
        stream_name=FIREHOSE_STREAM_NAME, region=cdk.Aws.REGION),
      assumed_by=aws_iam.ServicePrincipal("firehose.amazonaws.com"),
      #XXX: use inline_policies to work around https://github.com/aws/aws-cdk/issues/5221
      inline_policies={
        "firehose_role_policy": firehose_role_policy_doc
      }
    )

    lambda_proc = cfn.ProcessorProperty(
      type="Lambda",
      parameters=[
        cfn.ProcessorParameterProperty(
          parameter_name="LambdaArn",
          # parameter_value='{}:{}'.format(schema_validator_lambda_fn.function_arn, schema_validator_lambda_fn.current_version.version)
          parameter_value='{}:{}'.format(data_transform_lambda_fn.function_arn, data_transform_lambda_fn.latest_version.version)
        ),
        cfn.ProcessorParameterProperty(
          parameter_name="NumberOfRetries",
          parameter_value=str(FIREHOSE_LAMBDA_NUMBER_OF_RETRIES)
        ),
        cfn.ProcessorParameterProperty(
          parameter_name="RoleArn",
          parameter_value=firehose_role.role_arn
        ),
        cfn.ProcessorParameterProperty(
          parameter_name="BufferSizeInMBs",
          parameter_value=str(FIREHOSE_LAMBDA_BUFFER_SIZE)
        ),
        cfn.ProcessorParameterProperty(
          parameter_name="BufferIntervalInSeconds",
          parameter_value=str(FIREHOSE_LAMBDA_BUFFER_INTERVAL)
        )
      ]
    )

    firehose_processing_config = cfn.ProcessingConfigurationProperty(
      enabled=True,
      processors=[
        lambda_proc
      ]
    )

    ext_s3_dest_config = cfn.ExtendedS3DestinationConfigurationProperty(
      bucket_arn=s3_bucket.bucket_arn,
      role_arn=firehose_role.role_arn,
      buffering_hints={
        "intervalInSeconds": FIREHOSE_BUFFER_INTERVAL,
        "sizeInMBs": FIREHOSE_BUFFER_SIZE
      },
      cloud_watch_logging_options={
        "enabled": True,
        "logGroupName": firehose_log_group_name,
        "logStreamName": "S3Delivery"
      },
      compression_format="UNCOMPRESSED", # [GZIP | HADOOP_SNAPPY | Snappy | UNCOMPRESSED | ZIP]
      data_format_conversion_configuration={
        "enabled": False
      },
      dynamic_partitioning_configuration={
        "enabled": False
      },
      error_output_prefix=FIREHOSE_TO_S3_ERROR_OUTPUT_PREFIX,
      prefix=FIREHOSE_TO_S3_PREFIX,
      processing_configuration=firehose_processing_config
    )

    firehose_to_s3_delivery_stream = aws_kinesisfirehose.CfnDeliveryStream(self, "KinesisFirehoseToS3",
      delivery_stream_name=FIREHOSE_STREAM_NAME,
      delivery_stream_type="KinesisStreamAsSource",
      kinesis_stream_source_configuration={
        "kinesisStreamArn": source_kinesis_stream_arn,
        "roleArn": firehose_role.role_arn
      },
      extended_s3_destination_configuration=ext_s3_dest_config
    )

    self.s3_dest_bucket_name = s3_bucket.bucket_name
    self.s3_dest_folder_name = FIREHOSE_TO_S3_OUTPUT_FOLDER

    cdk.CfnOutput(self, '{}_S3DestBucket'.format(self.stack_name), value=s3_bucket.bucket_name, export_name='S3DestBucket')
    cdk.CfnOutput(self, '{}_KinesisDataFirehoseName'.format(self.stack_name),
      value=firehose_to_s3_delivery_stream.delivery_stream_name, export_name='KinesisDataFirehoseName')

