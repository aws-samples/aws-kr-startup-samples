import json
import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

REGION = os.environ.get("AWS_REGION")
HOST = os.environ.get("HOST")

def handler(event, context):
    print(f"Event: {json.dumps(event)}")

    if event['RequestType'] == 'Create':
        try:
            endpoint = event['ResourceProperties']['CollectionEndpoint']
            index_name = event['ResourceProperties']['IndexName']

            url = f"{endpoint}/{index_name}"

            index_body = {
                "settings": {
                    "index": {
                        "knn": True
                    }
                },
                "mappings": {
                    "properties": {
                        "vector_field": {
                            "type": "knn_vector",
                            "dimension": 1024,
                            "method": {
                                "name": "hnsw",
                                "engine": "faiss"
                            }
                        },
                        "text": {"type": "text"},
                        "chunk_type": {"type": "keyword"},
                        "chunk_name": {"type": "text"},
                        "filepath": {"type": "text"},
                        "language": {"type": "keyword"},
                        "commit": {"type": "keyword"}
                    }
                }
            }

            # Use urllib3 instead of requests
            session = boto3.Session()
            credentials = session.get_credentials()

            auth = AWSV4SignerAuth(credentials, REGION, 'aoss')

            client = OpenSearch(
                hosts = [{'host': HOST, 'port': 443}],
                http_auth = auth,
                use_ssl = True,
                verify_certs = True,
                connection_class = RequestsHttpConnection,
                pool_maxsize = 20
            )

            # Actually create the index and check the result
            response = client.indices.create(index=index_name, body=index_body)
            
            # Check if index creation was successful
            if response.get('acknowledged', False):
                print(f"Index '{index_name}' created successfully")
                
                # Optionally verify the index exists
                if client.indices.exists(index=index_name):
                    print(f"Verified: Index '{index_name}' exists")
                else:
                    raise Exception(f"Index creation may have failed - index '{index_name}' does not exist")
            else:
                raise Exception(f"Index creation was not acknowledged: {response}")

        except Exception as e:
            print(f"Error: {str(e)}")
            raise e
    elif event['RequestType'] == 'Delete':
        # Handle deletion if needed
        try:
            index_name = event['ResourceProperties']['IndexName']
            session = boto3.Session()
            credentials = session.get_credentials()
            auth = AWSV4SignerAuth(credentials, REGION, 'aoss')
            client = OpenSearch(
                hosts = [{'host': HOST, 'port': 443}],
                http_auth = auth,
                use_ssl = True,
                verify_certs = True,
                connection_class = RequestsHttpConnection,
            )
            if client.indices.exists(index=index_name):
                client.indices.delete(index=index_name)
                print(f"Index '{index_name}' deleted")
        except Exception as e:
            print(f"Error during deletion: {str(e)}")
            # Don't raise on delete errors to allow stack cleanup
            
    return {
        'PhysicalResourceId': f"{event['ResourceProperties']['IndexName']}-index",
        'Data': {'IndexName': event['ResourceProperties']['IndexName']}
    }