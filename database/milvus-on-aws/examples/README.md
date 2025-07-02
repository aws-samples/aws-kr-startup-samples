# Milvus Examples

This directory contains Python examples for working with Milvus vector database.

## Setup

1. Configure Examples Environment

```bash
# Get the Milvus LoadBalancer endpoint
export MILVUS_ENDPOINT=$(kubectl get svc -n milvus milvus -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Milvus endpoint: $MILVUS_ENDPOINT"

cd examples

envsubst < .env.template > .env
cat .env
```

2. Install Python Dependencies

```bash
# Create and use virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

## Examples

### 1. Connection Test
Test basic connectivity to Milvus:
```bash
python test_connection.py
```

### 2. Basic Insert and Search
Demonstrates basic vector operations (idempotent):
```bash
python test_insert_search.py
```

### 3. RAG (Retrieval-Augmented Generation)
Semantic search example for RAG applications (idempotent):
```bash
python test_rag.py
```

### 4. Interactive Streamlit Demo
Web-based interactive demo for exploring Milvus features:
```bash
streamlit run streamlit_demo.py --server.address=0.0.0.0
```

This will start a web interface accessible at:
- Local: http://localhost:8501
- Network: http://your-ip:8501

The Streamlit demo provides:
- Interactive vector search and similarity matching
- Real-time data insertion and querying
- Visual exploration of vector operations
- Collection management through a web UI

### 5. Utilities
Collection management utilities:
```bash
# List all collections
python utils.py list

# Get collection information
python utils.py info <collection_name>

# Drop a collection
python utils.py drop <collection_name>
```

## Notes

- All examples are designed to be idempotent (safe to run multiple times)
- Make sure your Milvus cluster is running and accessible before running examples
- The Streamlit demo requires all dependencies from requirements.txt to be installed
