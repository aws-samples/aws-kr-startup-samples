#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_athena
)
from constructs import Construct


class AthenaNamedQueryStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, athena_work_group_name, s3_json_location, s3_parquet_location, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    query_for_json_table = '''/* Create your database */
CREATE DATABASE IF NOT EXISTS mydatabase;

/* Create table with partitions */
CREATE EXTERNAL TABLE `mydatabase.web_log_json`(
  `userId` string,
  `sessionId` string,
  `referrer` string,
  `userAgent` string,
  `ip` string,
  `hostname` string,
  `os` string,
  `timestamp` timestamp,
  `uri` string)
PARTITIONED BY (
  `year` int,
  `month` int,
  `day` int,
  `hour` int)
ROW FORMAT SERDE
  'org.openx.data.jsonserde.JsonSerDe'
STORED AS INPUTFORMAT
  'org.apache.hadoop.mapred.TextInputFormat'
OUTPUTFORMAT
  'org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat'
LOCATION
  '{s3_location}';

/* Next we will load the partitions for this table */
MSCK REPAIR TABLE mydatabase.web_log_json;

/* Check the partitions */
SHOW PARTITIONS mydatabase.web_log_json;

SELECT COUNT(*) FROM mydatabase.web_log_json;
'''.format(s3_location=s3_json_location)

    named_query_for_json_table = aws_athena.CfnNamedQuery(self, "MyAthenaCfnNamedQuery1",
      database="default",
      query_string=query_for_json_table,

      # the properties below are optional
      description="Sample Hive DDL statement to create a partitioned table pointing to web log data (json)",
      name="Create Web Log table (json) with partitions",
      work_group=athena_work_group_name
    )

    query_for_parquet_table = '''/* Create your database */
CREATE DATABASE IF NOT EXISTS mydatabase;

/* Create table with partitions */
CREATE EXTERNAL TABLE `mydatabase.web_log_parquet`(
  `userId` string,
  `sessionId` string,
  `referrer` string,
  `userAgent` string,
  `ip` string,
  `hostname` string,
  `os` string,
  `timestamp` timestamp,
  `uri` string)
PARTITIONED BY (
  `year` int,
  `month` int,
  `day` int,
  `hour` int)
ROW FORMAT SERDE
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  '{s3_location}';

/* Next we will load the partitions for this table */
MSCK REPAIR TABLE mydatabase.web_log_parquet;

/* Check the partitions */
SHOW PARTITIONS mydatabase.web_log_parquet;

SELECT COUNT(*) FROM mydatabase.web_log_parquet;
'''.format(s3_location=s3_parquet_location)

    named_query_for_parquet_table = aws_athena.CfnNamedQuery(self, "MyAthenaCfnNamedQuery2",
      database="default",
      query_string=query_for_parquet_table,

      # the properties below are optional
      description="Sample Hive DDL statement to create a partitioned table pointing to web log data (parquet)",
      name="Create Web Log table (parquet) with partitions",
      work_group=athena_work_group_name
    )

