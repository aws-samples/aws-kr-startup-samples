#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import boto3
from typing import List


def get_cfn_outputs(stack_name: str, region_name: str='us-east-1') -> List:
    cfn = boto3.client('cloudformation', region_name=region_name)
    outputs = {}
    for output in cfn.describe_stacks(StackName=stack_name)['Stacks'][0]['Outputs']:
        outputs[output['OutputKey']] = output['OutputValue']
    return outputs

def get_secret_name(stack_name: str, region_name: str='us-east-1'):
    cf_client = boto3.client('cloudformation', region_name=region_name)
    response = cf_client.describe_stacks(StackName=stack_name)
    outputs = response["Stacks"][0]["Outputs"]

    secrets = [e for e in outputs if e['ExportName'] == 'VectorDBSecret'][0]
    secret_name = secrets['OutputValue']
    return secret_name

def get_secret(secret_id: str, region_name: str='us-east-1'):
    client = boto3.client('secretsmanager', region_name=region_name)
    response = client.get_secret_value(SecretId=secret_id)
    secret = json.loads(response['SecretString'])
    return secret
