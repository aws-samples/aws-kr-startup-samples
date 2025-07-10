#!/usr/bin/env python3
"""
Utility functions for Milvus operations
"""

import os
from dotenv import load_dotenv
from pymilvus import connections, utility, Collection

# Load environment variables
load_dotenv()

# Configuration from .env
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))


def connect():
    """Connect to Milvus"""
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")


def disconnect():
    """Disconnect from Milvus"""
    try:
        connections.disconnect("default")
        print("Disconnected from Milvus")
    except:
        pass


def list_collections():
    """List all collections"""
    collections = utility.list_collections()
    print(f"Collections: {collections}")
    return collections


def drop_collection(collection_name):
    """Drop a collection if it exists"""
    if utility.has_collection(collection_name):
        collection = Collection(collection_name)
        collection.drop()
        print(f"Collection '{collection_name}' dropped")
        return True
    else:
        print(f"Collection '{collection_name}' does not exist")
        return False


def collection_info(collection_name):
    """Get information about a collection"""
    if not utility.has_collection(collection_name):
        print(f"Collection '{collection_name}' does not exist")
        return None

    collection = Collection(collection_name)
    print(f"Collection: {collection_name}")
    print(f"  Schema: {collection.schema}")
    print(f"  Number of entities: {collection.num_entities}")
    print(f"  Indexes: {collection.indexes}")

    return {
        "name": collection_name,
        "schema": collection.schema,
        "num_entities": collection.num_entities,
        "indexes": collection.indexes,
    }


def get_sample_documents():
    """Get sample documents for testing"""
    return [
        {
            "text": "Amazon Web Services (AWS) is a comprehensive cloud computing platform that offers over 200 services including compute, storage, database, networking, and machine learning capabilities.",
            "source": "AWS Overview",
        },
        {
            "text": "Milvus is an open-source vector database built for AI applications. It provides high-performance similarity search and supports various index types for efficient vector retrieval.",
            "source": "Milvus Documentation",
        },
        {
            "text": "Kubernetes is an open-source container orchestration platform that automates deployment, scaling, and management of containerized applications across clusters of hosts.",
            "source": "Kubernetes Guide",
        },
        {
            "text": "Vector databases are specialized databases designed to store and query high-dimensional vectors efficiently. They are essential for AI applications like recommendation systems and semantic search.",
            "source": "Vector Database Primer",
        },
        {
            "text": "Amazon EKS (Elastic Kubernetes Service) is a managed Kubernetes service that makes it easy to run Kubernetes on AWS without needing to install and operate your own Kubernetes control plane.",
            "source": "EKS Documentation",
        },
    ]


def main():
    """Main function for utility operations"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python utils.py <command> [args]")
        print("Commands:")
        print("  list                    - List all collections")
        print("  info <collection_name>  - Get collection information")
        print("  drop <collection_name>  - Drop a collection")
        return

    command = sys.argv[1]

    try:
        connect()

        if command == "list":
            list_collections()
        elif command == "info" and len(sys.argv) > 2:
            collection_info(sys.argv[2])
        elif command == "drop" and len(sys.argv) > 2:
            drop_collection(sys.argv[2])
        else:
            print(f"Unknown command: {command}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        disconnect()


if __name__ == "__main__":
    main()
