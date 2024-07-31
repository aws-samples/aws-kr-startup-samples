#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import os
import datetime
import time
import random

import boto3

random.seed(47)

DRY_RUN = (os.getenv('DRY_RUN', 'false').lower() == 'true')
AWS_REGION = os.getenv('REGION_NAME', 'us-east-1')

OLD_DATABASE = os.getenv('OLD_DATABASE')
OLD_TABLE_NAME = os.getenv('OLD_TABLE_NAME')
NEW_DATABASE = os.getenv('NEW_DATABASE')
NEW_TABLE_NAME = os.getenv('NEW_TABLE_NAME')
WORK_GROUP = os.getenv('ATHENA_WORK_GROUP', 'primary')
OLD_TABLE_LOCATION_PREFIX = os.getenv('OLD_TABLE_LOCATION_PREFIX')
OUTPUT_PREFIX = os.getenv('OUTPUT_PREFIX')
STAGING_OUTPUT_PREFIX = os.getenv('STAGING_OUTPUT_PREFIX')
COLUMN_NAMES = os.getenv('COLUMN_NAMES', '*')

EXTERNAL_LOCATION_FMT = '''{output_prefix}/year={year}/month={month:02}/day={day:02}/hour={hour:02}/'''

CTAS_QUERY_FMT = '''CREATE TABLE {new_database}.tmp_{new_table_name}
WITH (
  external_location='{location}',
  format = 'PARQUET',
  parquet_compression = 'SNAPPY')
AS SELECT {columns}
FROM {old_database}.{old_table_name}
WHERE year={year} AND month={month} AND day={day} AND hour={hour}
WITH DATA
'''

def run_alter_table_add_partition(athena_client, basic_dt, database_name, table_name, output_prefix):
  year, month, day, hour = (basic_dt.year, basic_dt.month, basic_dt.day, basic_dt.hour)

  tmp_table_name = '{table}_{year}{month:02}{day:02}{hour:02}'.format(table=table_name,
      year=year, month=month, day=day, hour=hour)

  output_location = '{}/alter_table_{}'.format(STAGING_OUTPUT_PREFIX, tmp_table_name)

  alter_table_stmt = '''ALTER TABLE {database}.{table_name} ADD IF NOT EXISTS'''.format(database=database_name,
    table_name=table_name)

  partition_expr = '''PARTITION (year={year}, month={month}, day={day}, hour={hour}) LOCATION "{output_prefix}/year={year}/month={month:02}/day={day:02}/hour={hour:02}/"'''

  partition_expr_list = []
  for i in (1, 0, -1):
     dt = basic_dt - datetime.timedelta(hours=i)
     year, month, day, hour = (dt.year, dt.month, dt.day, dt.hour)
     part_expr = partition_expr.format(year=year, month=month, day=day, hour=hour, output_prefix=output_prefix)
     partition_expr_list.append(part_expr)

  query = '{} {}'.format(alter_table_stmt, '\n'.join(partition_expr_list))
  print('[INFO] QueryString:\n{}'.format(query), file=sys.stderr)
  print('[INFO] OutputLocation: {}'.format(output_location), file=sys.stderr)

  if DRY_RUN:
    print('[INFO] End of dry-run', file=sys.stderr)
    return

  response = athena_client.start_query_execution(
    QueryString=query,
    ResultConfiguration={
      'OutputLocation': output_location
    },
    WorkGroup=WORK_GROUP
  )
  print('[INFO] QueryExecutionId: {}'.format(response['QueryExecutionId']), file=sys.stderr)


def run_drop_tmp_table(athena_client, basic_dt):
  year, month, day, hour = (basic_dt.year, basic_dt.month, basic_dt.day, basic_dt.hour)

  tmp_table_name = '{table}_{year}{month:02}{day:02}{hour:02}'.format(table=NEW_TABLE_NAME,
      year=year, month=month, day=day, hour=hour)

  output_location = '{}/tmp_{}'.format(STAGING_OUTPUT_PREFIX, tmp_table_name)
  query = 'DROP TABLE IF EXISTS {database}.tmp_{table_name}'.format(database=NEW_DATABASE,
      table_name=tmp_table_name)

  print('[INFO] QueryString:\n{}'.format(query), file=sys.stderr)
  print('[INFO] OutputLocation: {}'.format(output_location), file=sys.stderr)

  if DRY_RUN:
    print('[INFO] End of dry-run', file=sys.stderr)
    return

  response = athena_client.start_query_execution(
    QueryString=query,
    ResultConfiguration={
      'OutputLocation': output_location
    },
    WorkGroup=WORK_GROUP
  )
  print('[INFO] QueryExecutionId: {}'.format(response['QueryExecutionId']), file=sys.stderr)


def run_ctas(athena_client, basic_dt):
  year, month, day, hour = (basic_dt.year, basic_dt.month, basic_dt.day, basic_dt.hour)

  new_table_name = '{table}_{year}{month:02}{day:02}{hour:02}'.format(table=NEW_TABLE_NAME,
    year=year, month=month, day=day, hour=hour)

  output_location = '{}/tmp_{}'.format(STAGING_OUTPUT_PREFIX, new_table_name)
  external_location = EXTERNAL_LOCATION_FMT.format(output_prefix=OUTPUT_PREFIX,
    year=year, month=month, day=day, hour=hour)

  query = CTAS_QUERY_FMT.format(new_database=NEW_DATABASE, new_table_name=new_table_name,
    old_database=OLD_DATABASE, old_table_name=OLD_TABLE_NAME, columns=COLUMN_NAMES,
    year=year, month=month, day=day, hour=hour, location=external_location)

  print('[INFO] QueryString:\n{}'.format(query), file=sys.stderr)
  print('[INFO] ExternalLocation: {}'.format(external_location), file=sys.stderr)
  print('[INFO] OutputLocation: {}'.format(output_location), file=sys.stderr)

  if DRY_RUN:
    print('[INFO] End of dry-run', file=sys.stderr)
    return

  response = athena_client.start_query_execution(
    QueryString=query,
    QueryExecutionContext={
      'Database': NEW_DATABASE
    },
    ResultConfiguration={
      'OutputLocation': output_location
    },
    WorkGroup=WORK_GROUP
  )
  print('[INFO] QueryExecutionId: {}'.format(response['QueryExecutionId']), file=sys.stderr)


def lambda_handler(event, context):
  event_dt = datetime.datetime.strptime(event['time'], "%Y-%m-%dT%H:%M:%SZ")
  prev_basic_dt, basic_dt = [event_dt - datetime.timedelta(hours=e) for e in (2, 1)]

  client = boto3.client('athena', region_name=AWS_REGION)
  run_drop_tmp_table(client, prev_basic_dt)

  if not DRY_RUN:
    print('[INFO] Wait for a few seconds until dropping old table', file=sys.stderr)
    time.sleep(10)

  run_alter_table_add_partition(client, basic_dt,
    database_name=OLD_DATABASE,
    table_name=OLD_TABLE_NAME,
    output_prefix=OLD_TABLE_LOCATION_PREFIX)

  if not DRY_RUN:
    print('[INFO] Wait for a few seconds until adding partitions to table: %s.%s' % (OLD_DATABASE, OLD_TABLE_NAME), file=sys.stderr)
    time.sleep(10)

  run_alter_table_add_partition(client, basic_dt,
    database_name=NEW_DATABASE,
    table_name=NEW_TABLE_NAME,
    output_prefix=OUTPUT_PREFIX)

  if not DRY_RUN:
    print('[INFO] Wait for a few seconds until adding partitions to table: %s.%s' % (NEW_DATABASE, NEW_TABLE_NAME), file=sys.stderr)
    time.sleep(10)

  run_ctas(client, basic_dt)


if __name__ == '__main__':
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument('-dt', '--basic-datetime', default=datetime.datetime.today().strftime('%Y-%m-%dT%H:05:00Z'),
    help='The scheduled event occurrence time ex) 2020-02-28T03:05:00Z')
  parser.add_argument('--region-name', default='us-east-1',
    help='aws region name')
  parser.add_argument('--old-database', default='mydatabase',
    help='aws athena source database name used by ctas query')
  parser.add_argument('--old-table-name', default='restapi_access_log_json',
    help='aws athena source table name used by ctas query')
  parser.add_argument('--new-database', default='mydatabase',
    help='aws athena target database name for merged files')
  parser.add_argument('--new-table-name', default='restapi_access_log_parquet',
    help='aws athena target table name for merged files')
  parser.add_argument('--work-group', default='primary',
    help='aws athena work group')
  parser.add_argument('--old-table-location-prefix', required=True,
    help='s3 path for aws athena source table')
  parser.add_argument('--output-prefix', required=True,
    help='s3 path for aws athena target table')
  parser.add_argument('--staging-output-prefix', required=True,
    help='s3 path for aws athena tmp table')
  parser.add_argument('--column-names', default='*',
    help='selectable column names of aws athena source table')
  parser.add_argument('--run', action='store_true',
    help='run ctas query')

  options = parser.parse_args()

  DRY_RUN = False if options.run else True
  AWS_REGION = options.region_name
  OLD_DATABASE = options.old_database
  OLD_TABLE_NAME= options.old_table_name
  NEW_DATABASE = options.new_database
  NEW_TABLE_NAME = options.new_table_name
  WORK_GROUP = options.work_group
  OLD_TABLE_LOCATION_PREFIX = options.old_table_location_prefix
  OUTPUT_PREFIX = options.output_prefix
  STAGING_OUTPUT_PREFIX = options.staging_output_prefix
  COLUMN_NAMES = options.column_names

  event = {
    "id": "cdc73f9d-aea9-11e3-9d5a-835b769c0d9c",
    "detail-type": "Scheduled Event",
    "source": "aws.events",
    "account": "123456789012",
    "time": options.basic_datetime, # ex) "2020-02-28T03:05:00Z"
    "region": AWS_REGION, # ex) "us-east-1"
    "resources": [
      f"arn:aws:events:{AWS_REGION}:123456789012:rule/ExampleRule"
    ],
    "detail": {}
  }
  print('[DEBUG] event:\n{}'.format(event), file=sys.stderr)
  lambda_handler(event, {})
