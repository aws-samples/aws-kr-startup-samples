#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  # aws_s3 as s3,
  aws_kinesisfirehose
)
from constructs import Construct

from aws_cdk.aws_kinesisfirehose import CfnDeliveryStream as cfn


class FirehoseToIcebergStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
               data_transform_lambda_fn, source_kinesis_stream, s3_bucket,
               firehose_role, **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    data_firehose_configuration = self.node.try_get_context("data_firehose_configuration")

    firehose_stream_name = data_firehose_configuration["stream_name"]
    firehose_log_group_name = f"/aws/kinesisfirehose/{firehose_stream_name}"

    firehose_buffering_hints = data_firehose_configuration["buffering_hints"]
    firehose_buffer_size = firehose_buffering_hints["size_in_mbs"]
    firehose_buffer_interval = firehose_buffering_hints["interval_in_seconds"]

    transform_records_with_aws_lambda = data_firehose_configuration["transform_records_with_aws_lambda"]
    firehose_lambda_buffer_size = transform_records_with_aws_lambda["buffer_size"]
    firehose_lambda_buffer_interval = transform_records_with_aws_lambda["buffer_interval"]
    firehose_lambda_number_of_retries = transform_records_with_aws_lambda["number_of_retries"]

    s3_output_prefix = data_firehose_configuration["output_prefix"]
    s3_error_output_prefix = data_firehose_configuration["error_output_prefix"]

    lambda_proc = cfn.ProcessorProperty(
      type="Lambda",
      parameters=[
        cfn.ProcessorParameterProperty(
          parameter_name="LambdaArn",
          parameter_value='{}:{}'.format(
            data_transform_lambda_fn.function_arn,
            data_transform_lambda_fn.latest_version.version
          )
        ),
        cfn.ProcessorParameterProperty(
          parameter_name="NumberOfRetries",
          parameter_value=str(firehose_lambda_number_of_retries)
        ),
        cfn.ProcessorParameterProperty(
          parameter_name="RoleArn",
          parameter_value=firehose_role.role_arn
        ),
        cfn.ProcessorParameterProperty(
          parameter_name="BufferSizeInMBs",
          parameter_value=str(firehose_lambda_buffer_size)
        ),
        cfn.ProcessorParameterProperty(
          parameter_name="BufferIntervalInSeconds",
          parameter_value=str(firehose_lambda_buffer_interval)
        )
      ]
    )

    firehose_processing_config = cfn.ProcessingConfigurationProperty(
      enabled=True,
      processors=[
        lambda_proc
      ]
    )

    dest_iceberg_table_config = data_firehose_configuration["destination_iceberg_table_configuration"]

    iceberg_dest_config = cfn.IcebergDestinationConfigurationProperty(
      catalog_configuration=cfn.CatalogConfigurationProperty(
        catalog_arn=f"arn:aws:glue:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:catalog"
      ),
      role_arn=firehose_role.role_arn,
      s3_configuration=cfn.S3DestinationConfigurationProperty(
        bucket_arn=s3_bucket.bucket_arn,
        role_arn=firehose_role.role_arn,
        buffering_hints={
          "intervalInSeconds": firehose_buffer_interval,
          "sizeInMBs": firehose_buffer_size
        },
        cloud_watch_logging_options={
          "enabled": True,
          "logGroupName": firehose_log_group_name,
          "logStreamName": "DestinationDelivery"
        },
        compression_format="UNCOMPRESSED", # [GZIP | HADOOP_SNAPPY | Snappy | UNCOMPRESSED | ZIP]
        error_output_prefix=s3_error_output_prefix,
        prefix=s3_output_prefix,
      ),
      buffering_hints={
        "intervalInSeconds": firehose_buffer_interval,
        "sizeInMBs": firehose_buffer_size
      },
      cloud_watch_logging_options={
        "enabled": True,
        "logGroupName": firehose_log_group_name,
        "logStreamName": "DestinationDelivery"
      },
      destination_table_configuration_list=[
        cfn.DestinationTableConfigurationProperty(
          destination_database_name=dest_iceberg_table_config["database_name"],
          destination_table_name=dest_iceberg_table_config["table_name"],
          s3_error_output_prefix=s3_error_output_prefix,
          unique_keys=dest_iceberg_table_config["unique_keys"]
        )
      ],
      processing_configuration=firehose_processing_config,
      s3_backup_mode='FailedDataOnly'
    )

    delivery_stream = aws_kinesisfirehose.CfnDeliveryStream(self, "FirehoseToIceberg",
      delivery_stream_name=firehose_stream_name,
      delivery_stream_type="KinesisStreamAsSource",
      kinesis_stream_source_configuration={
        "kinesisStreamArn": source_kinesis_stream.stream_arn,
        "roleArn": firehose_role.role_arn
      },
      iceberg_destination_configuration=iceberg_dest_config,
      tags=[{"key": "Name", "value": firehose_stream_name}]
    )


    cdk.CfnOutput(self, 'SourceKinesisStreamName',
      value=source_kinesis_stream.stream_name,
      export_name=f'{self.stack_name}-SourceKinesisStreamName')
    cdk.CfnOutput(self, 'S3DestBucket',
      value=s3_bucket.bucket_name,
      export_name=f'{self.stack_name}-S3DestBucket')