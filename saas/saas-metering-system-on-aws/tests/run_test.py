#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import json
import random

import requests


def gen_params():
  CHARS = random.choice(['', 'lowercase', 'uppercase', 'letters'])
  LENGTH = random.randint(0, 20)
  NUM = random.randint(0, 5)

  payload = {}
  if CHARS:
    payload['chars'] = CHARS
  if LENGTH:
    payload['len'] = LENGTH
  if NUM:
    payload['num'] = NUM

  return payload


def main():
  parser = argparse.ArgumentParser()

  parser.add_argument('--execution-id', help='api gateway execution-id')
  parser.add_argument('--region-name', action='store', default='us-east-1',
    help='aws region name (default: us-east-1)')
  parser.add_argument('--auth-token', help='authorization token to access Rest APIs')
  parser.add_argument('--max-count', default=10, type=int, help='The max number of trials')
  parser.add_argument('--api-stage', default='prod', help='api stage name: [prod, dev] (default: prod)')
  parser.add_argument('--dry-run', action='store_true')

  options = parser.parse_args()

  EXECUTION_ID = options.execution_id
  REGION = options.region_name
  MY_ID_TOKEN = options.auth_token

  URL = f'https://{EXECUTION_ID}.execute-api.{REGION}.amazonaws.com/{options.api_stage}/random/strings'

  for _ in range(options.max_count):
    payload = gen_params()

    headers = {'Authorization': MY_ID_TOKEN} if MY_ID_TOKEN else {}
    if options.dry_run:
      query_strings = '&'.join([f"{k}={v}" for k, v in payload.items()])
      auth_header = f'--header "Authorization: {MY_ID_TOKEN}"' if headers else ""
      print(f"curl -XGET '{URL}?{query_strings}' {auth_header}")
      continue

    res = requests.get(URL, params=payload, headers=headers)
    output = res.json() if res.status_code == 200 else []
    print(res.status_code, json.dumps(output), res.url)


if __name__ == '__main__':
  main()

