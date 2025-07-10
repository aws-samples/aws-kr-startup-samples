#!/usr/bin/env python3
"""
Simple connection test for Milvus
"""

import os
from dotenv import load_dotenv
from pymilvus import connections, utility

# Load environment variables
load_dotenv()

# Connection details from .env
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))


def test_connection():
    """Test connection to Milvus"""
    try:
        # Connect to Milvus
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        print(f"✅ Successfully connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")

        # Check server version
        print(f"📋 Server version: {utility.get_server_version()}")

        # List existing collections
        collections = utility.list_collections()
        print(f"📚 Existing collections: {collections}")

        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    finally:
        try:
            connections.disconnect("default")
            print("🔌 Disconnected from Milvus")
        except:
            pass


if __name__ == "__main__":
    test_connection()
