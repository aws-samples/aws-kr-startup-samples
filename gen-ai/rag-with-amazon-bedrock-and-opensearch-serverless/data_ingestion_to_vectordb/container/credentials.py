#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4 expandtab

import json
import boto3

from opensearchpy import AWSV4SignerAuth


def get_credentials(secret_id: str, region_name: str) -> str:
    """
    Retrieve credentials password for given username from AWS SecretsManager
    """
    client = boto3.client('secretsmanager', region_name=region_name)
    response = client.get_secret_value(SecretId=secret_id)
    secrets_value = json.loads(response['SecretString'])

    return secrets_value


def get_auth(region_name: str) -> AWSV4SignerAuth:
    """
    Get AWSV4SignerAuth to access Amazon OpenSearch Serverless
    """
    credentials = boto3.Session(region_name=region_name).get_credentials()
    auth = AWSV4SignerAuth(credentials, region_name, 'aoss')

    return auth