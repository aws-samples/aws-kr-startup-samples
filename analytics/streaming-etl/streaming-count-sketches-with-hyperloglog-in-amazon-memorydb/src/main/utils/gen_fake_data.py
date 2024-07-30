#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import argparse
import collections
import datetime
import json
import random
import time
import traceback

import boto3

import mimesis

# Mimesis 5.0 supports Python 3.8, 3.9, and 3.10.
# The Mimesis 4.1.3 is the last to support Python 3.6 and 3.7
# For more information, see https://mimesis.name/en/latest/changelog.html#version-5-0-0
assert mimesis.__version__ == '4.1.3'

from mimesis import locales
from mimesis.schema import Field, Schema
from mimesis.providers.base import BaseProvider

random.seed(47)


class CustomDatetimeProvider(BaseProvider):
  class Meta:
    """Class for metadata."""
    name = "custom_datetime"

  def __init__(self, seed=47) -> None:
    super().__init__(seed=seed)
    self.random = random.Random(seed)

  def formated_datetime(self, fmt='%Y-%m-%dT%H:%M:%SZ', lt_now=False) -> str:
    CURRENT_YEAR = datetime.datetime.now().year
    CURRENT_MONTH = datetime.datetime.now().month
    CURRENT_DAY = datetime.datetime.now().day
    CURRENT_HOUR = datetime.datetime.now().hour
    CURRENT_MINUTE = datetime.datetime.now().minute
    CURRENT_SECOND = datetime.datetime.now().second

    if lt_now:
      random_time = datetime.time(
        self.random.randint(0, CURRENT_HOUR),
        self.random.randint(0, max(0, CURRENT_MINUTE-1)),
        self.random.randint(0, max(0, CURRENT_SECOND-1)),
        self.random.randint(0, 999999)
      )
    else:
      random_time = datetime.time(
        CURRENT_HOUR,
        CURRENT_MINUTE,
        self.random.randint(CURRENT_SECOND, 59),
        self.random.randint(0, 999999)
      )

    datetime_obj = datetime.datetime.combine(
      date=datetime.date(CURRENT_YEAR, CURRENT_MONTH, CURRENT_DAY),
      time=random_time,
    )

    return datetime_obj.strftime(fmt)


def mk_redis_key(json_data):
  REDIS_KEY_FORMAT = 'uv:site_id={site_id}:{daily_basic_dt}'

  user_id, site_id, event_time = [json_data[k] for k in ('user_id', 'site_id', 'event_time')]
  event_time = datetime.datetime.strptime(event_time, '%Y-%m-%d %H:%M:%S')
  daily_basic_dt = event_time.strftime('%Y%m%d')

  key = REDIS_KEY_FORMAT.format(site_id=site_id, daily_basic_dt=daily_basic_dt)
  return key


def put_records_to_kinesis(client, options, payload_list):

  if options.dry_run:
    print(json.dumps(payload_list, ensure_ascii=False))
    return

  try:
    response = client.put_records(Records=payload_list, StreamName=options.stream_name)
    failed_record_count = response['FailedRecordCount']
    if failed_record_count:
      print(f'[Kinesis Data Streams] FailedRecordCount={failed_record_count}', file=sys.stderr)
  except Exception as ex:
    traceback.print_exc()
    raise RuntimeError('[ERROR] Failed to put_records into stream: {}'.format(options.stream_name))


def main():
  parser = argparse.ArgumentParser()

  parser.add_argument('--region-name', action='store', default='us-east-1',
    help='aws region name (default: us-east-1)')
  parser.add_argument('--service-name', required=True, choices=['kinesis', 'console'])
  parser.add_argument('--stream-name', help='The name of the stream to put the data record into (default: 10)')
  parser.add_argument('--max-count', default=10, type=int, help='The max number of records to put (default: 10)')
  parser.add_argument('--dry-run', action='store_true')
  parser.add_argument('--verbose', action='store_true', help='Show debug logs')

  options = parser.parse_args()

  #XXX: For more information about synthetic data schema, see
  # https://github.com/aws-samples/aws-glue-streaming-etl-blog/blob/master/config/generate_data.py
  _ = Field(locale=locales.EN, providers=[CustomDatetimeProvider])

  _schema = Schema(schema=lambda: {
    "user_id": f"u-{_('identifier', mask='###-##')}",
    "site_id": _("choice", items=[489, 715, 283, 190, 875]),
    "event": _("choice", items=['view', 'like', 'cart', 'purchase']),
    "sku": _("pin", mask='@@####@@@@'),
    "amount":  _("integer_number", start=1, end=10),
    "event_time": _("custom_datetime.formated_datetime", fmt="%Y-%m-%d %H:%M:%S", lt_now=True),
  })

  client = boto3.client(options.service_name, region_name=options.region_name) if options.service_name != 'console' else None

  uv_counter_keys = collections.Counter()
  cnt = 0

  payload_list = []
  for record in _schema.create(options.max_count):
    cnt += 1

    redis_key = mk_redis_key(record)
    uv_counter_keys[redis_key] += 1

    data = f"{json.dumps(record)}\n"
    if options.dry_run or options.service_name == 'console':
      print(data, file=sys.stderr)
      continue

    if options.verbose:
      print(data, file=sys.stderr)

    partition_key = 'part-{:05}'.format(random.randint(1, 1024))
    payload_list.append({'Data': data, 'PartitionKey': partition_key})

    if len(payload_list) % 10 == 0:
      put_records_to_kinesis(client, options, payload_list)
      payload_list = []

    time.sleep(0.1)

  if payload_list:
    put_records_to_kinesis(client, options, payload_list)

  print(f'[INFO] Total {cnt} records are processed', file=sys.stderr)
  print('[INFO] Keys in Amazon MemoryDB:', file=sys.stderr)
  print('\n'.join([k for k in uv_counter_keys.keys()]), file=sys.stderr)


if __name__ == '__main__':
  main()
