#!/usr/bin/env python3
"""
Idempotent Milvus usage example with .env support
"""

import os
import random
from dotenv import load_dotenv
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility,
)

# Load environment variables
load_dotenv()

# Configuration from .env
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "example_collection")
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "128"))
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "500"))
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
DEFAULT_NPROBE = int(os.getenv("DEFAULT_NPROBE", "10"))


def connect_to_milvus():
    """Connect to Milvus cluster"""
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")


def create_or_get_collection():
    """Create collection if it doesn't exist, or get existing one"""
    if utility.has_collection(COLLECTION_NAME):
        print(
            f"Collection '{COLLECTION_NAME}' already exists, using existing collection"
        )
        collection = Collection(COLLECTION_NAME)

        # Drop existing data to make it truly idempotent
        print("Dropping existing data...")
        collection.drop()
        print("Existing collection dropped")

    # Define fields
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=MAX_TEXT_LENGTH),
    ]

    # Create schema
    schema = CollectionSchema(fields, "Example collection for vector search")

    # Create collection
    collection = Collection(COLLECTION_NAME, schema)
    print(f"Collection '{COLLECTION_NAME}' created successfully")

    return collection


def insert_data(collection):
    """Insert sample data into the collection"""
    # Generate sample data
    num_entities = 1000
    entities = [
        [i for i in range(num_entities)],  # IDs
        [
            [random.random() for _ in range(VECTOR_DIM)] for _ in range(num_entities)
        ],  # Embeddings
        [f"Sample text {i}" for i in range(num_entities)],  # Text data
    ]

    # Insert data
    insert_result = collection.insert(entities)
    print(f"Inserted {len(insert_result.primary_keys)} entities")

    # Flush to ensure data is written
    collection.flush()
    print("Data flushed to storage")


def create_or_recreate_index(collection):
    """Create or recreate index for efficient vector search"""
    # Check if index exists and drop it
    try:
        indexes = collection.indexes
        if indexes:
            print("Dropping existing index...")
            collection.drop_index()
            print("Existing index dropped")
    except Exception as e:
        print(f"No existing index to drop: {e}")

    # Create new index
    index_params = {
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128},
    }

    collection.create_index("embedding", index_params)
    print("Index created on embedding field")


def search_vectors(collection):
    """Perform vector similarity search"""
    # Load collection into memory
    collection.load()
    print("Collection loaded into memory")

    # Generate query vector
    query_vector = [[random.random() for _ in range(VECTOR_DIM)]]

    # Search parameters
    search_params = {"metric_type": "L2", "params": {"nprobe": DEFAULT_NPROBE}}

    # Perform search
    results = collection.search(
        query_vector,
        "embedding",
        search_params,
        limit=DEFAULT_TOP_K,
        output_fields=["text"],
    )

    print(f"\nSearch Results (Top {DEFAULT_TOP_K}):")
    for hits in results:
        for hit in hits:
            print(
                f"ID: {hit.id}, Distance: {hit.distance:.4f}, Text: {hit.entity.get('text')}"
            )


def main():
    """Main function to demonstrate Milvus usage"""
    try:
        print("🚀 Starting idempotent Milvus example...")

        # Connect to Milvus
        connect_to_milvus()

        # Create or get collection (idempotent)
        collection = create_or_get_collection()

        # Insert data
        insert_data(collection)

        # Create or recreate index (idempotent)
        create_or_recreate_index(collection)

        # Search vectors
        search_vectors(collection)

        print("\n✅ Milvus example completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        try:
            connections.disconnect("default")
            print("🔌 Disconnected from Milvus")
        except:
            pass


if __name__ == "__main__":
    main()
