#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import base64
import collections
import json
import os
import traceback
from datetime import datetime

import boto3
from rediscluster import RedisCluster


REDIS_KEY_FORMAT = 'uv:site_id={site_id}:{daily_basic_dt}'

AWS_REGION = os.getenv('REGION_NAME', 'us-east-1')

REDIS_HOST = os.environ['REDIS_HOST']
MEMORYDB_SECRET_ID = os.environ['MEMORYDB_SECRET_NAME']

redis_client = None


def get_credentials(secret_id: str, region_name: str) -> str:
  client = boto3.client('secretsmanager', region_name=region_name)
  res = client.get_secret_value(SecretId=secret_id)
  secrets_value = json.loads(res['SecretString'])
  return secrets_value


def get_or_create_redis_client():
  global redis_client

  if redis_client is None:
    creds = get_credentials(MEMORYDB_SECRET_ID, AWS_REGION)
    USER, PASSWORD = creds['username'], creds['password']

    redis_cluster_options = {
      'startup_nodes': [{"host": REDIS_HOST, "port": 6379}],
      'decode_responses': True,
      'skip_full_coverage_check': True,
      'ssl': True,
      'username': USER,
      'password': PASSWORD
    }

    redis_client = RedisCluster(**redis_cluster_options)

  return redis_client


def list_split(arr, n):
    for i in range(0, len(arr), n):
      yield arr[i:i+n]


def lambda_handler(event, context):
  redis_client = get_or_create_redis_client()
  if redis_client.ping():
    print('[INFO] Connected to MemoryDB')
  else:
    print('[ERROR] Not Connected to MemoryDB')
    raise RuntimeError()

  counter = collections.OrderedDict([
    ('reads', 0),
    ('writes', 0),
    ('insert_errors', 0),
    ('parse_errors', 0)
  ])

  data = {}
  for record in event['Records']:
    try:
      counter['reads'] += 1
      payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
      json_data = json.loads(payload)

      user_id, site_id, event_time = [json_data[k] for k in ['user_id', 'site_id', 'event_time']]
      event_time = datetime.strptime(event_time, '%Y-%m-%d %H:%M:%S')
      daily_basic_dt = event_time.strftime('%Y%m%d')
      k = f'{site_id}:{daily_basic_dt}'
      data.setdefault(k, set())
      data[k].add(user_id)
    except Exception as ex:
      counter['parse_errors'] += 1
      traceback.print_exc()

  site_list = list(data.keys())
  chunk_size = 3 # need to be adjusted
  for elems in list_split(site_list, chunk_size):
    try:
      with redis_client.pipeline() as pipe:
        for key_elem in elems:
          site_id, daily_basic_dt = key_elem.split(':')
          k = REDIS_KEY_FORMAT.format(site_id=site_id, daily_basic_dt=daily_basic_dt)
          pipe.pfadd(k, *data[key_elem])
          pipe.expire(k, 86400)
        pipe.execute()
      counter['writes'] += len(elems)
    except Exception as ex:
      counter['insert_errors'] += 1
      traceback.print_exc()

  print('[INFO]', ', '.join(['{}={}'.format(k, v) for k, v in counter.items()]), file=sys.stderr)


if __name__ == '__main__':
  utc_now = datetime.utcnow()
  utc_dt = utc_now.strftime('%Y-%m-%d %H:%M')
  kinesis_data = [
    '''{{"user_id": "user-672", "site_id": 283, "event": "cart", "sku": "AN9254HKOG", "amount": 3, "event_time": "{utc_dt}:46"}}'''.format(utc_dt=utc_dt),
    '''{{"user_id": "user-646", "site_id": 715, "event": "purchase", "sku": "HL0484IHRV", "amount": 2, "event_time": "{utc_dt}:09"}}'''.format(utc_dt=utc_dt),
    '''{{"user_id": "user-190", "site_id": 489, "event": "purchase", "sku": "KN1658KLLE", "amount": 7, "event_time": "{utc_dt}:07"}}'''.format(utc_dt=utc_dt),
    '''{{"user_id": "user-190", "site_id": 283, "event": "like", "sku": "FT2329FULN", "amount": 5, "event_time": "{utc_dt}:48"}}'''.format(utc_dt=utc_dt),
    '''{{"user_id": "user-190", "site_id": 283, "event": "purchase", "sku": "GB0895CLWG", "amount": 8, "event_time": "{utc_dt}:40"}}'''.format(utc_dt=utc_dt),
    '''{{"user_id": "user-875", "site_id": 489, "event": "purchase", "sku": "ZD8540CVGL", "amount": 8, "event_time": "{utc_dt}:56"}}'''.format(utc_dt=utc_dt),
    '''{{"user_id": "user-033", "site_id": 283, "event": "like", "sku": "VT3927XDIQ", "amount": 8, "event_time": "{utc_dt}:58"}}'''.format(utc_dt=utc_dt),
    '''{{"user_id": "user-190", "site_id": 715, "event": "cart", "sku": "QR5297TXTR", "amount": 5, "event_time": "{utc_dt}:05"}}'''.format(utc_dt=utc_dt),
    '''{{"user_id": "user-190", "site_id": 715, "event": "like", "sku": "QA2140DLAI", "amount": 3, "event_time": "{utc_dt}:57"}}'''.format(utc_dt=utc_dt),
    '''{{"user_id": "user-646", "site_id": 283, "event": "like", "sku": "ZY5054EUYE", "amount": 2, "event_time": "{utc_dt}:44"}}'''.format(utc_dt=utc_dt),
  ]

  records = [{
    "eventID": "shardId-000000000000:49545115243490985018280067714973144582180062593244200961",
    "eventVersion": "1.0",
    "kinesis": {
      "approximateArrivalTimestamp": int(utc_now.timestamp()),
      "partitionKey": "partitionKey-1",
      "data": base64.b64encode(e.encode('utf-8')),
      "kinesisSchemaVersion": "1.0",
      "sequenceNumber": "49545115243490985018280067714973144582180062593244200961"
    },
    "invokeIdentityArn": "arn:aws:iam::EXAMPLE",
    "eventName": "aws:kinesis:record",
    "eventSourceARN": "arn:aws:kinesis:EXAMPLE",
    "eventSource": "aws:kinesis",
    "awsRegion": "us-east-1"
    } for e in kinesis_data]
  event = {"Records": records}

  lambda_handler(event, {})
