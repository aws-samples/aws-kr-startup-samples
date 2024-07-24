#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging
import sys
import time

import boto3

from datetime import datetime

from opensearchpy import (
    OpenSearch,
    RequestsHttpConnection,
    AWSV4SignerAuth
)


logger = logging.getLogger()
logging.basicConfig(format='%(asctime)s,%(module)s,%(processName)s,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stderr)


def update_aoss_data_access_policy_with_caller_arn(policy_name: str, caller_arn: str, region_name: str='us-east-1'):
    """
    Update the data access policy to add the caller arn as a trusted principal.
    """
    aos_client = boto3.client("opensearchserverless", region_name=region_name)
    response = aos_client.get_access_policy(name=policy_name, type="data")
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        logger.info(response['ResponseMetadata'])
        return False

    access_policy_detail = response['accessPolicyDetail']
    updated_data_access_policy = list(access_policy_detail['policy'])
    if caller_arn in updated_data_access_policy[0]['Principal']:
        logger.info("Do nothing.")
        return True

    updated_data_access_policy[0]['Principal'].append(caller_arn)
    response = aos_client.update_access_policy(
        name=policy_name,
        policyVersion=access_policy_detail['policyVersion'],
        policy=json.dumps(updated_data_access_policy),
        description=f"Policy updated at {datetime.now()}",
        type="data"
    )

    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        return False

    logger.info(response['ResponseMetadata'])
    logger.info("Updated data access policy, sleeping for 30 secs for permissions to propagate")
    time.sleep(30)

    return True


def get_aws_auth(region_name: str='us-east-1') -> AWSV4SignerAuth:
    """
    Get AWSV4SignerAuth to access Amazon OpenSearch Serverless
    """
    credentials = boto3.Session(region_name=region_name).get_credentials()
    auth = AWSV4SignerAuth(credentials, region_name, 'aoss')

    return auth


def check_if_index_exists(index_name: str, host: str, auth: AWSV4SignerAuth) -> OpenSearch:
    aos_client = OpenSearch(
        hosts=[{'host': host.replace("https://", ""), 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    exists = aos_client.indices.exists(index_name)
    logger.info(f"index_name={index_name}, exists={exists}")
    return exists
