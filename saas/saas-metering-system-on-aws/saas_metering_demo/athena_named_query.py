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
CREATE EXTERNAL TABLE `mydatabase.restapi_access_log_json`(
  `requestId` string,
  `ip` string,
  `user` string, 
  `requestTime` timestamp, 
  `httpMethod` string, 
  `resourcePath` string, 
  `status` string,
  `protocol` string, 
  `responseLength` integer)
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
MSCK REPAIR TABLE mydatabase.restapi_access_log_json;

/* Check the partitions */
SHOW PARTITIONS mydatabase.restapi_access_log_json;

SELECT COUNT(*) FROM mydatabase.restapi_access_log_json;
'''.format(s3_location=s3_json_location)

    named_query_for_json_table = aws_athena.CfnNamedQuery(self, "MyAthenaCfnNamedQuery1",
      database="default",
      query_string=query_for_json_table,

      # the properties below are optional
      description="Sample Hive DDL statement to create a partitioned table pointing to web log data (json)",
      name="JSON Web Log table with partitions",
      work_group=athena_work_group_name
    )

    query_for_parquet_table = '''/* Create your database */
CREATE DATABASE IF NOT EXISTS mydatabase;

/* Create table with partitions */
CREATE EXTERNAL TABLE `mydatabase.restapi_access_log_parquet`(
  `requestId` string,
  `ip` string,
  `user` string, 
  `requestTime` timestamp, 
  `httpMethod` string, 
  `resourcePath` string, 
  `status` string,
  `protocol` string, 
  `responseLength` integer)
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
MSCK REPAIR TABLE mydatabase.restapi_access_log_parquet;

/* Check the partitions */
SHOW PARTITIONS mydatabase.restapi_access_log_parquet;

SELECT COUNT(*) FROM mydatabase.restapi_access_log_parquet;
'''.format(s3_location=s3_parquet_location)

    named_query_for_parquet_table = aws_athena.CfnNamedQuery(self, "MyAthenaCfnNamedQuery2",
      database="default",
      query_string=query_for_parquet_table,

      # the properties below are optional
      description="Sample Hive DDL statement to create a partitioned table pointing to web log data (parquet)",
      name="Parquet Web Log table with partitions",
      work_group=athena_work_group_name
    )

    ctas_query = '''/* Drop a temp table */
DROP TABLE IF EXISTS mydatabase.tmp_restapi_access_log_parquet_2023013111;

/* Add partitions to the JSON table */
ALTER TABLE mydatabase.restapi_access_log_json ADD IF NOT EXISTS 
PARTITION (year=2023, month=1, day=31, hour=11) LOCATION "{s3_json_location}/year=2023/month=01/day=31/hour=11/"
PARTITION (year=2023, month=1, day=31, hour=12) LOCATION "{s3_json_location}/year=2023/month=01/day=31/hour=12/"
PARTITION (year=2023, month=1, day=31, hour=13) LOCATION "{s3_json_location}/year=2023/month=01/day=31/hour=13/";

/* Add partitions to the Parquet table */
ALTER TABLE mydatabase.restapi_access_log_parquet ADD IF NOT EXISTS 
PARTITION (year=2023, month=1, day=31, hour=11) LOCATION "{s3_parquet_location}/year=2023/month=01/day=31/hour=11/"
PARTITION (year=2023, month=1, day=31, hour=12) LOCATION "{s3_parquet_location}/parquet-data/year=2023/month=01/day=31/hour=12/"
PARTITION (year=2023, month=1, day=31, hour=13) LOCATION "{s3_parquet_location}/year=2023/month=01/day=31/hour=13/";

/* Run CTAS */
CREATE TABLE mydatabase.tmp_restapi_access_log_parquet_2023013112
WITH (
external_location='{s3_parquet_location}/year=2023/month=01/day=31/hour=12/',
format = 'PARQUET',
parquet_compression = 'SNAPPY')
AS SELECT requestId,ip,user,requestTime,httpMethod,resourcePath,status,protocol,responseLength
FROM mydatabase.restapi_access_log_json
WHERE year=2023 AND month=1 AND day=31 AND hour=12
WITH DATA;
'''.format(s3_json_location=s3_json_location, s3_parquet_location=s3_parquet_location)

    named_ctas_query = aws_athena.CfnNamedQuery(self, "MyAthenaCfnNamedQuery3",
      database="default",
      query_string=ctas_query,

      # the properties below are optional
      description="Sample CTAS query to convert json to parquet",
      name="CTAS Query on Web Log table",
      work_group=athena_work_group_name
    )

