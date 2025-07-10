#!/usr/bin/env python3
"""
Idempotent RAG (Retrieval-Augmented Generation) example with Milvus and .env support
"""

import os
from dotenv import load_dotenv
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility,
)
from sentence_transformers import SentenceTransformer
from utils import get_sample_documents

# Load environment variables
load_dotenv()

# Configuration from .env
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "knowledge_base")
RAG_VECTOR_DIM = int(os.getenv("RAG_VECTOR_DIM", "384"))
RAG_MAX_TEXT_LENGTH = int(os.getenv("RAG_MAX_TEXT_LENGTH", "2000"))
RAG_MAX_SOURCE_LENGTH = int(os.getenv("RAG_MAX_SOURCE_LENGTH", "200"))
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
DEFAULT_NPROBE = int(os.getenv("DEFAULT_NPROBE", "10"))


class MilvusRAG:
    def __init__(self):
        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )  # Lightweight embedding model
        self.collection = None

    def connect(self):
        """Connect to Milvus"""
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")

    def create_or_recreate_knowledge_base(self):
        """Create or recreate knowledge base collection (idempotent)"""
        # Drop existing collection if it exists
        if utility.has_collection(RAG_COLLECTION_NAME):
            print(f"Collection '{RAG_COLLECTION_NAME}' already exists, dropping it...")
            collection = Collection(RAG_COLLECTION_NAME)
            collection.drop()
            print("Existing collection dropped")

        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(
                name="embedding", dtype=DataType.FLOAT_VECTOR, dim=RAG_VECTOR_DIM
            ),
            FieldSchema(
                name="text", dtype=DataType.VARCHAR, max_length=RAG_MAX_TEXT_LENGTH
            ),
            FieldSchema(
                name="source", dtype=DataType.VARCHAR, max_length=RAG_MAX_SOURCE_LENGTH
            ),
        ]

        schema = CollectionSchema(fields, "Knowledge base for RAG")
        self.collection = Collection(RAG_COLLECTION_NAME, schema)

        # Create index
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        self.collection.create_index("embedding", index_params)
        print(f"Knowledge base '{RAG_COLLECTION_NAME}' created with index")

    def add_documents(self, documents):
        """Add documents to the knowledge base"""
        texts = [doc["text"] for doc in documents]
        sources = [doc["source"] for doc in documents]

        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.model.encode(texts).tolist()

        # Insert data
        entities = [embeddings, texts, sources]
        insert_result = self.collection.insert(entities)
        self.collection.flush()
        print(f"Added {len(documents)} documents to knowledge base")

    def search_similar(self, query, top_k=None):
        """Search for similar documents"""
        if top_k is None:
            top_k = DEFAULT_TOP_K

        # Load collection
        self.collection.load()

        # Generate query embedding
        query_embedding = self.model.encode([query]).tolist()

        # Search
        search_params = {"metric_type": "COSINE", "params": {"nprobe": DEFAULT_NPROBE}}
        results = self.collection.search(
            query_embedding,
            "embedding",
            search_params,
            limit=top_k,
            output_fields=["text", "source"],
        )

        # Format results
        similar_docs = []
        for hits in results:
            for hit in hits:
                similar_docs.append(
                    {
                        "text": hit.entity.get("text"),
                        "source": hit.entity.get("source"),
                        "score": hit.score,
                    }
                )

        return similar_docs


def demo_rag():
    """Demonstrate RAG functionality"""
    print("🚀 Starting idempotent RAG example...")

    # Initialize RAG system
    rag = MilvusRAG()
    rag.connect()
    rag.create_or_recreate_knowledge_base()

    # Add documents
    sample_docs = get_sample_documents()
    rag.add_documents(sample_docs)

    # Example queries
    queries = [
        "What is a vector database?",
        "How does AWS help with cloud computing?",
        "Tell me about Kubernetes container orchestration",
    ]

    for query in queries:
        print(f"\n🔍 Query: {query}")
        print("-" * 50)

        similar_docs = rag.search_similar(query, top_k=3)

        for i, doc in enumerate(similar_docs, 1):
            print(f"{i}. Score: {doc['score']:.4f}")
            print(f"   Source: {doc['source']}")
            print(f"   Text: {doc['text'][:100]}...")
            print()


if __name__ == "__main__":
    try:
        demo_rag()
        print("✅ RAG example completed successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure to install required packages:")
        print("pip install -r requirements.txt")
        raise
    finally:
        try:
            connections.disconnect("default")
            print("🔌 Disconnected from Milvus")
        except:
            pass
