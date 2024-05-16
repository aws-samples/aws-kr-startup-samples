#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4 expandtab

import os
import sys

# this is needed because the credentials.py and sm_helper.py
# are in /code directory of the custom container we are going
# to create for Sagemaker Processing Job
sys.path.insert(1, '/code')

import glob
import time
import logging
import argparse
import multiprocessing as mp
from itertools import repeat
from functools import partial
from typing import (
    Tuple
)

import numpy as np

from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.document_loaders import ReadTheDocsLoader
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain.text_splitter import RecursiveCharacterTextSplitter

from opensearchpy import (
    OpenSearch,
    RequestsHttpConnection
)

from credentials import get_credentials


# global constants
MAX_OS_DOCS_PER_PUT = 500
TOTAL_INDEX_CREATION_WAIT_TIME = 60
PER_ITER_SLEEP_TIME = 5

logger = logging.getLogger()
logging.basicConfig(format='%(asctime)s,%(module)s,%(processName)s,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stderr)


def check_if_index_exists(index_name: str, host: str, http_auth: Tuple[str, str]) -> OpenSearch:
    aos_client = OpenSearch(
        hosts=[{'host': host.rstrip('/').replace("https://", ""), 'port': 443}],
        http_auth=http_auth,
        use_ssl=True,
        verify_certs=True,
        connection_class = RequestsHttpConnection
    )
    exists = aos_client.indices.exists(index_name)
    logger.info(f"index_name={index_name}, exists={exists}")
    return exists


def process_shard(shard, aws_region, os_index_name, os_domain_ep, os_http_auth) -> int:
    logger.info(f'Starting process_shard of {len(shard)} chunks.')
    st = time.time()

    embeddings = BedrockEmbeddings(
        model_id='amazon.titan-embed-text-v1',
        region_name=aws_region
    )

    docsearch = OpenSearchVectorSearch(index_name=os_index_name,
                                       embedding_function=embeddings,
                                       opensearch_url=os_domain_ep,
                                       http_auth=os_http_auth)

    docsearch.add_documents(documents=shard)

    et = time.time() - st
    logger.info(f'Shard completed in {et} seconds.')
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--opensearch-cluster-domain", type=str, default=None)
    parser.add_argument("--opensearch-secretid", type=str, default=None)
    parser.add_argument("--opensearch-index-name", type=str, default=None)
    parser.add_argument("--aws-region", type=str, default="us-east-1")
    parser.add_argument("--chunk-size-for-doc-split", type=int, default=500)
    parser.add_argument("--chunk-overlap-for-doc-split", type=int, default=30)
    parser.add_argument("--input-data-dir", type=str, default="/opt/ml/processing/input_data")
    parser.add_argument("--process-count", type=int, default=1)
    parser.add_argument("--create-index-hint-file", type=str, default="_create_index_hint")
    args, _ = parser.parse_known_args()

    logger.info("Received arguments {}".format(args))
    # list all the files
    files = glob.glob(os.path.join(args.input_data_dir, "*.*"))
    logger.info(f"there are {len(files)} files to process in the {args.input_data_dir} folder")

    # retrieve secret to talk to opensearch
    creds = get_credentials(args.opensearch_secretid, args.aws_region)
    http_auth = (creds['username'], creds['password'])

    loader = ReadTheDocsLoader(args.input_data_dir)
    text_splitter = RecursiveCharacterTextSplitter(
        # Set a really small chunk size, just to show.
        chunk_size=args.chunk_size_for_doc_split,
        chunk_overlap=args.chunk_overlap_for_doc_split,
        length_function=len,
    )

    # Stage one: read all the docs, split them into chunks.
    st = time.time()
    logger.info('Loading documents ...')
    docs = loader.load()

    # add a custom metadata field, such as timestamp
    for doc in docs:
        doc.metadata['timestamp'] = time.time()
        doc.metadata['embeddings_model'] = 'amazon.titan-embed-text-v1'
    chunks = text_splitter.create_documents([doc.page_content for doc in docs], metadatas=[doc.metadata for doc in docs])
    et = time.time() - st
    logger.info(f'Time taken: {et} seconds. {len(chunks)} chunks generated')


    db_shards = (len(chunks) // MAX_OS_DOCS_PER_PUT) + 1
    print(f'Loading chunks into vector store ... using {db_shards} shards')
    st = time.time()
    shards = np.array_split(chunks, db_shards)

    t1 = time.time()

    # first check if index exists, if it does then call the add_documents function
    # otherwise call the from_documents function which would first create the index
    # and then do a bulk add. Both add_documents and from_documents do a bulk add
    # but it is important to call from_documents first so that the index is created
    # correctly for K-NN
    index_exists = check_if_index_exists(args.opensearch_index_name,
                                         args.opensearch_cluster_domain,
                                         http_auth)

    embeddings = BedrockEmbeddings(
        model_id='amazon.titan-embed-text-v1',
        region_name=args.aws_region
    )

    if index_exists is False:
        # create an index if the create index hint file exists
        path = os.path.join(args.input_data_dir, args.create_index_hint_file)
        if os.path.isfile(path) is True:
            logger.info(f"index {args.opensearch_index_name} does not exist but {path} file is present so will create index")
            # by default langchain would create a k-NN index and the embeddings would be ingested as a k-NN vector type
            docsearch = OpenSearchVectorSearch.from_documents(index_name=args.opensearch_index_name,
                                                              documents=shards[0],
                                                              embedding=embeddings,
                                                              opensearch_url=args.opensearch_cluster_domain,
                                                              http_auth=http_auth)
            # we now need to start the loop below for the second shard
            shard_start_index = 1
        else:
            logger.info(f"index {args.opensearch_index_name} does not exist and {path} file is not present, "
                        f"will wait for some other node to create the index")
            shard_start_index = 0
            # start a loop to wait for index creation by another node
            time_slept = 0
            while True:
                logger.info(f"index {args.opensearch_index_name} still does not exist, sleeping...")
                time.sleep(PER_ITER_SLEEP_TIME)
                index_exists = check_if_index_exists(args.opensearch_index_name,
                                                     args.opensearch_cluster_domain,
                                                     http_auth)
                if index_exists is True:
                    logger.info(f"index {args.opensearch_index_name} now exists")
                    break
                time_slept += PER_ITER_SLEEP_TIME
                if time_slept >= TOTAL_INDEX_CREATION_WAIT_TIME:
                    logger.error(f"time_slept={time_slept} >= {TOTAL_INDEX_CREATION_WAIT_TIME}, not waiting anymore for index creation")
                    break

    else:
        logger.info(f"index={args.opensearch_index_name} does exists, going to call add_documents")
        shard_start_index = 0

    with mp.Pool(processes = args.process_count) as pool:
        results = pool.map(partial(process_shard,
                                   aws_region=args.aws_region,
                                   os_index_name=args.opensearch_index_name,
                                   os_domain_ep=args.opensearch_cluster_domain,
                                   os_http_auth=http_auth),
                           shards[shard_start_index:])

    t2 = time.time()
    logger.info(f'run time in seconds: {t2-t1:.2f}')
    logger.info("all done")
