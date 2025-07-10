#!/usr/bin/env python3
"""
Streamlit-based interactive demo for Milvus on AWS.

Allows users to:
- Initialize a Milvus collection with sample data.
- View collection statistics.
- Add new text documents to the collection.
- Upload and process PDF documents.
- Perform vector similarity searches.
- View a history of recent operations.
"""

import os
import time
import warnings
import asyncio
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_milvus import Milvus
from langchain.text_splitter import RecursiveCharacterTextSplitter
import fitz  # PyMuPDF

from utils import get_sample_documents

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

# Configuration
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
URI = f"http://{MILVUS_HOST}:{MILVUS_PORT}"
COLLECTION_NAME = "workshop_demo"

EMBEDDING_MODEL = "jhgan/ko-sroberta-nli"

# Page config
st.set_page_config(page_title="Milvus on AWS Workshop", page_icon="🚀", layout="wide")

# Initialize session state
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "operation_history" not in st.session_state:
    st.session_state.operation_history = []


@st.cache_resource
def get_embeddings():
    """Get HuggingFace embeddings."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def get_vector_store():
    """Initialize vector store using from_documents"""
    # Fix event loop issue for users running Streamlit on Windows
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    vector_store = Milvus(
        embedding_function=get_embeddings(),
        collection_name=COLLECTION_NAME,
        connection_args={"uri": URI},
        drop_old=False,
        auto_id=True,
    )

    return vector_store


def get_collection_stats(vector_store):
    """Get collection statistics"""
    try:
        return {
            "entity_count": vector_store.col.num_entities,
            "indexes": len(vector_store.col.indexes) if vector_store.col.indexes else 0,
        }
    except Exception as e:
        return {"error": str(e)}


def add_documents_to_store(vector_store, documents, source="text_input"):
    """Add new documents to the collection and log the operation."""
    start_time = time.time()
    vector_store.add_documents(documents)
    vector_store.col.flush()  # Explicitly flush to make data searchable
    duration = time.time() - start_time

    log_operation(
        "add", f"Added {len(documents)} documents from {source}", True, duration
    )
    st.success(f"✅ {len(documents)} documents added successfully from {source}")


def process_and_add_pdf(vector_store, uploaded_file):
    """Extract text from PDF, split it into chunks, and add to Milvus."""
    # This function now relies on Streamlit's top-level error handling
    with st.spinner(f"Processing {uploaded_file.name}..."):
        # 1. Read the entire PDF content using PyMuPDF
        pdf_doc = fitz.open(stream=uploaded_file.getvalue(), filetype="pdf")
        full_text = "".join(page.get_text() for page in pdf_doc)
        pdf_doc.close()

        if not full_text.strip():
            st.warning("PyMuPDF could not extract any text from the PDF.")
            return

        # 2. Split text using RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )
        chunks = text_splitter.split_text(full_text)

        # Create Document objects
        documents = [Document(page_content=chunk) for chunk in chunks]

        # Add source metadata to each final chunk
        for doc in documents:
            doc.metadata = {"source": uploaded_file.name, "category": "pdf"}

        if not documents:
            st.warning("Could not split the document into any chunks.")
            return

        # 3. Add the processed documents to Milvus
        st.info(f"Adding {len(documents)} chunks to the vector store...")
        add_documents_to_store(vector_store, documents, source=uploaded_file.name)


def search_documents(vector_store, query, k=5):
    """Search documents with performance tracking"""
    try:
        # Load collection into memory for searching to ensure all data is available
        vector_store.col.load()

        start_time = time.time()
        results = vector_store.similarity_search_with_score(query, k=k)
        duration = time.time() - start_time

        search_results = []
        for doc, distance in results:
            similarity = max(0, min(1, 1 - (distance / 2)))
            metadata = doc.metadata or {}
            search_results.append(
                {
                    "Distance": round(distance, 4),
                    "Similarity": round(similarity, 4),
                    "Text": doc.page_content,
                    "Source": metadata.get("source", "N/A"),
                    "Category": metadata.get("category", "unknown"),
                }
            )

        search_results.sort(key=lambda x: x["Similarity"], reverse=True)
        log_operation(
            "search", f"Found {len(results)} results for '{query}'", True, duration
        )

        return True, search_results
    except Exception as e:
        log_operation("search", f"Failed: {str(e)}", False)
        return False, f"❌ Search failed: {str(e)}"


def log_operation(operation, description, success, duration=None):
    """Log operations for monitoring"""
    log_entry = {
        "timestamp": time.time(),
        "operation": operation,
        "description": description,
        "success": success,
        "duration": duration,
    }

    st.session_state.operation_history.append(log_entry)

    if len(st.session_state.operation_history) > 20:
        st.session_state.operation_history = st.session_state.operation_history[-20:]


# Main UI
st.title("🚀 Milvus on AWS Workshop")
st.markdown("Interactive demo for vector search and document management")

# Connection info
with st.expander("Connection Details"):
    st.markdown(f"""
    - **Milvus Endpoint**: `{URI}`
    - **Collection Name**: `{COLLECTION_NAME}`
    - **Embedding Model**: `{EMBEDDING_MODEL}`
    """)

# Initialize vector store
if st.button("Connect and Initialize Collection"):
    with st.spinner("Connecting to Milvus and setting up collection..."):
        st.session_state.vector_store = get_vector_store()
        if st.session_state.vector_store:
            st.success("✅ Collection initialized with sample documents")
            st.rerun()
        # If initialization fails, get_vector_store() returns None
        # and displays its own error message. No 'else' needed here.

if st.session_state.vector_store:
    col1, col2 = st.columns([2, 1])

    with col1:
        # Collection Statistics
        st.subheader("📊 Collection Statistics")
        stats = get_collection_stats(st.session_state.vector_store)
        if "error" not in stats:
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Documents", stats["entity_count"])
            with col_b:
                st.metric("Indexes", stats["indexes"])

        # Document Operations
        st.subheader("📝 Document Operations")

        # Add Document
        with st.expander("➕ Insert Sample Documents", expanded=True):
            with st.form("add_sample_documents_form", clear_on_submit=True):
                submitted = st.form_submit_button("Add Sample Documents")
                if submitted:
                    with st.spinner("Adding sample documents..."):
                        # Correctly pass metadata including the source
                        docs = [
                            Document(
                                page_content=doc["text"],
                                metadata={
                                    "source": doc["source"],
                                    "category": "sample",
                                },
                            )
                            for doc in get_sample_documents()
                        ]
                        add_documents_to_store(
                            st.session_state.vector_store, docs, source="Sample Data"
                        )
                        st.rerun()

        with st.expander("➕ Insert Your Own Document", expanded=True):
            with st.form("add_document_form", clear_on_submit=True):
                new_text = st.text_area(
                    "Document text:", placeholder="Enter your document content..."
                )
                category = st.selectbox(
                    "Category:",
                    ["technology", "cloud", "database", "programming", "general"],
                    key="add_text_cat",
                )
                submitted = st.form_submit_button("Add Document")

                if submitted and new_text:
                    with st.spinner("Adding document..."):
                        doc = Document(
                            page_content=new_text,
                            metadata={"category": category, "source": "user_input"},
                        )
                        add_documents_to_store(st.session_state.vector_store, [doc])
                        st.rerun()

        # Upload PDF
        with st.expander("📂 Upload PDF Document"):
            uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
            if uploaded_file is not None:
                if st.button(f"Process and Add {uploaded_file.name}"):
                    process_and_add_pdf(st.session_state.vector_store, uploaded_file)
                    st.rerun()

        # Search Documents
        st.subheader("🔍 Search Documents")
        search_query = st.text_input(
            "Search query:", placeholder="What are you looking for?"
        )

        if st.button("Search") and search_query:
            with st.spinner("Searching..."):
                success, results = search_documents(
                    st.session_state.vector_store, search_query
                )
                if success:
                    st.subheader("Search Results")
                    if not results:
                        st.info("No results found.")
                    else:
                        df = pd.DataFrame(results)
                        display_cols = [
                            "Similarity",
                            "Text",
                            "Source",
                            "Category",
                            "Distance",
                        ]
                        existing_cols = [
                            col for col in display_cols if col in df.columns
                        ]
                        st.dataframe(
                            df[existing_cols], use_container_width=True, hide_index=True
                        )
                else:
                    st.error(results)

    with col2:
        # Operation History
        if st.session_state.operation_history:
            st.subheader("📈 Operation History")

            for op in reversed(st.session_state.operation_history[-5:]):
                status = "✅" if op["success"] else "❌"
                duration_text = (
                    f" ({op['duration']:.3f}s)" if op.get("duration") else ""
                )

                with st.expander(f"{status} {op['operation'].title()}{duration_text}"):
                    st.write(f"**Description:** {op['description']}")
                    st.write(
                        f"**Time:** {pd.to_datetime(op['timestamp'], unit='s').strftime('%H:%M:%S')}"
                    )
                    if op.get("duration"):
                        st.write(f"**Duration:** {op['duration']:.3f} seconds")

# Footer
st.markdown("---")
st.markdown("**Milvus on AWS Workshop** | Built with Streamlit & PyMuPDF")
