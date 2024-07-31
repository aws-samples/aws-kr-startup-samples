#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
#vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import base64
import json
import logging
import collections
from datetime import datetime

import fastavro

LOGGER = logging.getLogger()
if len(LOGGER.handlers) > 0:
  # The Lambda environment pre-configures a handler logging to stderr.
  # If a handler is already configured, `.basicConfig` does not execute.
  # Thus we set the level directly.
  LOGGER.setLevel(logging.INFO)
else:
  logging.basicConfig(level=logging.INFO)


ORIGINAL_SCHEMA = {
  'name': 'WebLogs',
  'type': 'record',
  'fields': [
    {
      'name': 'userId',
      'type': 'string'
    },
    {
      'name': 'sessionId',
      'type': 'string'
    },
    {
      'name': 'referrer',
      'type': ['string', 'null']
    },
    {
      'name': 'userAgent',
      'type': ['string', 'null']
    },
    {
      'name': 'ip',
      'type': 'string'
    },
    {
      'name': 'hostname',
      'type': 'string'
    },
    {
      'name': 'os',
      'type': ['string', 'null']
    },
    {
      'name': 'timestamp',
      'type': {
        'type': 'string',
        'logicalType': 'datetime'
      }
    },
    {
      'name': 'uri',
      'type': 'string'
    }
  ]
}


def read_datetime(data, writer_schema=None, reader_schema=None):
  return datetime.strptime(data, '%Y-%m-%dT%H:%M:%SZ')

def prepare_datetime(data, schema):
  """Converts datetime.datetime to string representing the date and time"""
  if isinstance(data, datetime):
    return datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
  else:
    try:
      dt = datetime.strptime(data, '%Y-%m-%dT%H:%M:%SZ')
      return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except Exception as ex:
      return None

fastavro.read.LOGICAL_READERS["string-datetime"] = read_datetime
fastavro.write.LOGICAL_WRITERS["string-datetime"] = prepare_datetime

PARSED_SCHEMA = fastavro.parse_schema(ORIGINAL_SCHEMA)

def check_schema(record):
  try:
    return fastavro.validation.validate(record, PARSED_SCHEMA, raise_errors=False)
  except Exception as ex:
    LOGGER.error(ex)
    return False

# Signature for all Lambda functions that user must implement
def lambda_handler(firehose_records_input, context):
  LOGGER.debug("Received records for processing from DeliveryStream: {deliveryStreamArn}, Region: {region}, and InvocationId: {invocationId}".format(
    deliveryStreamArn=firehose_records_input['deliveryStreamArn'],
    region=firehose_records_input['region'],
    invocationId=firehose_records_input['invocationId']))

  # Create return value.
  firehose_records_output = {'records': []}

  counter = collections.Counter(total=0, valid=0, invalid=0)

  # Create result object.
  # Go through records and process them
  for firehose_record_input in firehose_records_input['records']:
    counter['total'] += 1

    # Get user payload
    payload = base64.b64decode(firehose_record_input['data'])
    json_value = json.loads(payload)

    LOGGER.debug("Record that was received: {}".format(json_value))

    #TODO: check if schema is valid
    is_valid = check_schema(json_value)
    counter['valid' if is_valid else 'invalid'] += 1

    # Create output Firehose record and add modified payload and record ID to it.
    firehose_record_output = {
      'recordId': firehose_record_input['recordId'],
      #XXX: convert JSON to JSONLine
      'data': base64.b64encode(payload.rstrip(b'\n') + b'\n'),

      # The status of the data transformation of the record.
      # The possible values are: 
      #  Ok (the record was transformed successfully),
      #  Dropped (the record was dropped intentionally by your processing logic),
      # and ProcessingFailed (the record could not be transformed).
      # If a record has a status of Ok or Dropped, Kinesis Data Firehose considers it successfully processed.
      #  Otherwise, Kinesis Data Firehose considers it unsuccessfully processed.

      # 'ProcessFailed' record will be put into error bucket in S3
      'result': 'Ok' if is_valid else 'ProcessingFailed' # [Ok, Dropped, ProcessingFailed]
    }

    # Must set proper record ID
    # Add the record to the list of output records.
    firehose_records_output['records'].append(firehose_record_output)

  LOGGER.info(', '.join("{}={}".format(k, v) for k, v in counter.items()))

  # At the end return processed records
  return firehose_records_output


if __name__ == '__main__':
  import pprint

  record_list = [
    {
      "userId": "897bef5f-294d-4ecc-a3b6-ef2844958720",
      "sessionId": "a5aa20a72c9e37588f9bbeaa",
      "referrer": "brandon.biz",
      "userAgent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; de) Opera 8.52",
      "ip": "202.165.71.49",
      "hostname": "toxic.tokyo",
      "os": "openSUSE",
      "timestamp": "2022-09-16T07:35:46Z",
      "uri": "https://phones.madrid/2012/02/12/bed-federal-in-wireless-scientists-shoes-walker-those-premier-younger?lane=outcomes&acc=memories"
    },
    {
      "userId": "70b1f606-aa63-47fb-bc92-76de9c59d064",
      "sessionId": "928e78473db8449b17644b2c",
      # missing optional data
      # "referrer": "toe.gq",
      "userAgent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 8.53",
      "ip": "12.166.113.176",
      "hostname": "drivers.glass",
      "os": "Windows 8.1",
      "timestamp": "2022-09-16T07:52:47Z",
      "uri": "https://aaa.gov/2022/04/29/cialis-prayer-presentations-completed-avenue-vision?trucks=cut&indeed=members"
    },
    {
      "userId": "897bef5f-294d-4ecc-a3b6-ef2844958720",
      "sessionId": "a5aa20a72c9e37588f9bbeaa",
      "referrer": "brandon.biz",
      "userAgent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; de) Opera 8.52",
      "ip": "202.165.71.49",
      "hostname": "toxic.tokyo",
      "os": "openSUSE",
      # invalid datetime format
      "timestamp": "2022-09-16 07:35:46",
      "uri": "https://phones.madrid/2012/02/12/bed-federal-in-wireless-scientists-shoes-walker-those-premier-younger?lane=outcomes&acc=memories"
    },
    {
      # missing required data
      # "userId": "045e63c7-b276-4117-9706-7c2e3b87d5f5",
      "sessionId": "abfd47eb7dd7b8aeec0555a7",
      "referrer": "transfer.edu",
      "userAgent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; de) Opera 9.50",
      "ip": "170.128.148.234",
      "hostname": "propecia.tc",
      "os": "Lubuntu",
      "timestamp": "2022-09-16T07:46:04Z",
      "uri": "https://pee.cloud/2019/06/15/alan-publish-perl-snow-notification-gap-improvement-guaranteed-changed-determining?casino=admissions&cottage=hotel"
    },
    {
      "userId": "e504cd9d-30da-497f-8f28-2b3f64220e16",
      "sessionId": "fd4807ab825ee8bd950b1e8b",
      "referrer": "liquid.aquitaine",
      "userAgent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0; en) Opera 8.02",
      # mismatched data type
      "ip": 212234672,
      "hostname": "consequently.com",
      "os": "Gentoo",
      "timestamp": "2022-09-16T07:13:29Z",
      "uri": "https://railway.sz/2014/10/30/use-phone-task-marketplace?pot=it&album=cook"
    }
  ]

  for record in record_list:
    event = {
      "invocationId": "invocationIdExample",
      "deliveryStreamArn": "arn:aws:kinesis:EXAMPLE",
      "region": "us-east-1",
      "records": [
        {
          "recordId": "49546986683135544286507457936321625675700192471156785154",
          "approximateArrivalTimestamp": 1495072949453,
          "data": base64.b64encode(json.dumps(record).encode('utf-8'))
        }
      ]
    }

    res = lambda_handler(event, {})
    for elem in res['records']:
      print(f"[{elem['result']}]")
      print(base64.b64decode(elem['data']).decode('utf-8'))

