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
from functools import partial

import urllib

import numpy as np

from langchain_community.document_loaders import ReadTheDocsLoader
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter

from credentials import get_credentials
from sm_helper import create_sagemaker_embeddings_from_js_model


logger = logging.getLogger()
logging.basicConfig(format='%(asctime)s,%(module)s,%(processName)s,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stderr)


def process_shard(shard, embeddings_model_endpoint_name, aws_region, collection_name, connection_string) -> int:
    logger.info(f'Starting process_shard of {len(shard)} chunks.')
    st = time.time()

    embeddings = create_sagemaker_embeddings_from_js_model(embeddings_model_endpoint_name, aws_region)

    vectordb = PGVector.from_existing_index(
        embedding=embeddings,
        collection_name=collection_name,
        connection=connection_string)

    vectordb.add_documents(documents=shard)

    et = time.time() - st
    logger.info(f'Shard completed in {et} seconds.')
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--pgvector-secretid", type=str, default=None)
    parser.add_argument("--pgvector-collection-name", type=str, default=None)

    parser.add_argument("--aws-region", type=str, default="us-east-1")
    parser.add_argument("--embeddings-model-endpoint-name", type=str, default=None)
    parser.add_argument("--chunk-size-for-doc-split", type=int, default=500)
    parser.add_argument("--chunk-overlap-for-doc-split", type=int, default=30)
    parser.add_argument("--input-data-dir", type=str, default="/opt/ml/processing/input_data")
    parser.add_argument("--max-docs-per-put", type=int, default=10)
    parser.add_argument("--process-count", type=int, default=1)
    parser.add_argument("--create-index-hint-file", type=str, default="_create_index_hint")

    args, _ = parser.parse_known_args()
    logger.info("Received arguments {}".format(args))

    # list all the files
    files = glob.glob(os.path.join(args.input_data_dir, "*.*"))
    logger.info(f"there are {len(files)} files to process in the {args.input_data_dir} folder")

    # retrieve secret to talk to Amazon Aurora Postgresql
    secret = get_credentials(args.pgvector_secretid, args.aws_region)
    db_username = secret['username']
    db_password = urllib.parse.quote_plus(secret['password'])
    db_port = secret['port']
    db_host = secret['host']

    CONNECTION_STRING = PGVector.connection_string_from_db_params(
        driver = 'psycopg',
        user = db_username,
        password = db_password,
        host = db_host,
        port = db_port,
        database = ''
    )

    logger.info(f'input-data-dir: {args.input_data_dir}')
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
    logger.info(f'{len(docs)} documents have been loaded')

    # add a custom metadata field, such as timestamp
    for doc in docs:
        doc.metadata['timestamp'] = time.time()
        doc.metadata['embeddings_model'] = args.embeddings_model_endpoint_name
    chunks = text_splitter.create_documents([doc.page_content for doc in docs], metadatas=[doc.metadata for doc in docs])

    et = time.time() - st
    logger.info(f'Time taken: {et} seconds. {len(chunks)} chunks generated')

    db_shards = (len(chunks) // args.max_docs_per_put) + 1
    print(f'Loading chunks into vector store ... using {db_shards} shards')

    st = time.time()
    shards = np.array_split(chunks, db_shards)

    path = os.path.join(args.input_data_dir, args.create_index_hint_file)
    if os.path.isfile(path) is True:
        logger.info(f"{path} file is present, "
                    f"will try to create the {args.pgvector_collection_name} collection")

        embeddings = create_sagemaker_embeddings_from_js_model(args.embeddings_model_endpoint_name, args.aws_region)
        _ = PGVector(collection_name=args.pgvector_collection_name,
                     connection=CONNECTION_STRING,
                     embeddings=embeddings)
    else:
        logger.info(f"{path} file is not present, "
                    f"will wait for some other node to create the {args.pgvector_collection_name} collection")
        time.sleep(5)

    with mp.Pool(processes = args.process_count) as pool:
        results = pool.map(partial(process_shard,
                                   embeddings_model_endpoint_name=args.embeddings_model_endpoint_name,
                                   aws_region=args.aws_region,
                                   collection_name=args.pgvector_collection_name,
                                   connection_string=CONNECTION_STRING),
                           shards)

    et = time.time() - st
    logger.info(f'run time in seconds: {et:.2f}')
    logger.info("all done")
