#!/usr/bin/env python3
"""
Streamlit-based interactive demo for Milvus on EKS.

Allows users to:
- Initialize a Milvus collection with sample data.
- View collection statistics.
- Add new documents to the collection.
- Perform vector similarity searches.
- View a history of recent operations.
"""

import streamlit as st
import os
from dotenv import load_dotenv
import pandas as pd
import time
import warnings
import asyncio
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_milvus import Milvus

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

# Configuration
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
URI = f"http://{MILVUS_HOST}:{MILVUS_PORT}"
COLLECTION_NAME = "workshop_demo"

# Page config
st.set_page_config(page_title="Milvus on EKS Workshop", page_icon="🚀", layout="wide")

# Initialize session state
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "operation_history" not in st.session_state:
    st.session_state.operation_history = []


def get_vector_store():
    """Initialize vector store using from_documents"""
    # Fix event loop issue for users running Streamlit on Windows
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    embeddings = HuggingFaceEmbeddings(model_name="Qwen/Qwen3-Embedding-0.6B")

    # Initial documents
    initial_docs = [
        Document(
            page_content="Amazon Web Services (AWS) is a comprehensive cloud computing platform.",
            metadata={"category": "cloud"},
        ),
        Document(
            page_content="Machine Learning algorithms learn patterns from data automatically.",
            metadata={"category": "machine learning"},
        ),
        Document(
            page_content="Kubernetes orchestrates containerized applications across clusters.",
            metadata={"category": "kubernetes"},
        ),
        Document(
            page_content="Vector databases store high-dimensional vectors for AI applications.",
            metadata={"category": "database"},
        ),
        Document(
            page_content="Python is a versatile programming language for data science.",
            metadata={"category": "programming"},
        ),
    ]

    vector_store = Milvus.from_documents(
        documents=initial_docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        connection_args={"uri": URI},
        drop_old=False,
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


def add_document(vector_store, text, category="general"):
    """Add a new document to the collection"""
    try:
        doc = Document(page_content=text, metadata={"category": category})

        start_time = time.time()
        vector_store.add_documents([doc])
        duration = time.time() - start_time

        log_operation("add", f"Added: '{text[:50]}...'", True, duration)
        return True, f"✅ Document added successfully"
    except Exception as e:
        log_operation("add", f"Failed: {str(e)}", False)
        return False, f"❌ Add failed: {str(e)}"


def search_documents(vector_store, query, k=5):
    """Search documents with performance tracking"""
    try:
        start_time = time.time()
        results = vector_store.similarity_search_with_score(query, k=k)
        duration = time.time() - start_time

        search_results = []
        for doc, distance in results:
            similarity = max(0, min(1, 1 - (distance / 2)))
            search_results.append(
                {
                    "Distance": round(distance, 4),
                    "Similarity": round(similarity, 4),
                    "Text": doc.page_content,
                    "Source": doc.metadata.get("source", "manual_input"),
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


def process_uploaded_file(uploaded_file, vector_store):
    """Process uploaded file and add to Milvus"""
    try:
        filename = uploaded_file.name
        print(f"📁 Processing file: {filename}")

        # Extract text content
        if filename.lower().endswith(".pdf"):
            text_content = extract_pdf_with_pymupdf(uploaded_file)
        elif filename.lower().endswith(".txt"):
            text_content = uploaded_file.read().decode("utf-8")
        else:
            return False, f"Unsupported file type: {filename}"

        if text_content and len(text_content.strip()) > 0:
            print(f"📝 Extracted {len(text_content)} characters")

            # Create document and add to vector store
            from langchain_core.documents import Document

            doc = Document(
                page_content=text_content,
                metadata={"source": filename, "type": "uploaded_file"},
            )

            print(f"🔄 Generating embedding...")
            vector_store.add_documents([doc])
            print(f"✅ Successfully stored in Milvus")

            log_operation(
                "process", f"Processed: {filename} ({len(text_content)} chars)", True
            )
            return True, f"File processed successfully: {filename}"
        else:
            print(f"❌ No text extracted from {filename}")
            return False, f"Could not extract text from {filename}"

    except Exception as e:
        print(f"❌ Error processing {filename}: {str(e)}")
        log_operation("process", f"Failed: {str(e)}", False)
        return False, f"Processing failed: {str(e)}"


def extract_pdf_with_pymupdf(uploaded_file):
    """Extract text from PDF using PyMuPDF with optimized settings"""
    try:
        import pymupdf
        from io import BytesIO

        print(f"📝 Processing PDF with PyMuPDF...")

        # Read file content
        file_content = uploaded_file.read()

        # Open PDF document
        doc = pymupdf.open(stream=file_content, filetype="pdf")
        print(f"📄 PDF has {len(doc)} pages")

        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Extract text with layout preservation
            page_text = page.get_text("text")

            if page_text.strip():
                # Clean up excessive whitespace while preserving structure
                cleaned_text = "\n".join(
                    [line.strip() for line in page_text.split("\n") if line.strip()]
                )

                if cleaned_text:
                    text_parts.append(f"=== Page {page_num + 1} ===\n{cleaned_text}")
                    print(
                        f"📄 Page {page_num + 1}: extracted {len(cleaned_text)} characters"
                    )
                else:
                    print(f"📄 Page {page_num + 1}: no readable text")
            else:
                print(f"📄 Page {page_num + 1}: no text found")

        doc.close()

        if text_parts:
            full_text = "\n\n".join(text_parts)
            print(f"✅ PyMuPDF extracted {len(full_text)} total characters")
            return full_text
        else:
            print(f"⚠️ No text could be extracted from PDF")
            return "No readable text found in PDF"

    except ImportError:
        error_msg = "PyMuPDF not installed. Install with: pip install pymupdf"
        print(f"❌ {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"PyMuPDF processing error: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


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

# Initialize vector store
if st.button("Initialize Collection"):
    with st.spinner("Setting up collection..."):
        try:
            st.session_state.vector_store = get_vector_store()
            st.success("✅ Collection initialized with sample documents")
        except Exception as e:
            st.error(f"❌ Setup failed: {str(e)}")

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
        with st.expander("➕ Add Document", expanded=True):
            tab1, tab2 = st.tabs(["Text Input", "File Upload"])

            with tab1:
                with st.form("add_document_form", clear_on_submit=True):
                    new_text = st.text_area(
                        "Document text:", placeholder="Enter your document content..."
                    )
                    submitted = st.form_submit_button("Add Document")

                    if submitted and new_text:
                        with st.spinner("Adding document..."):
                            success, message = add_document(
                                st.session_state.vector_store, new_text
                            )
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

            with tab2:
                uploaded_file = st.file_uploader(
                    "Choose a file",
                    type=["txt", "pdf"],
                    help="Upload PDF or TXT files for processing",
                )

                if uploaded_file and st.button("Upload & Process"):
                    with st.spinner("Processing file..."):
                        success, message = process_uploaded_file(
                            uploaded_file, st.session_state.vector_store
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

                st.info("⚡ Using PyMuPDF for fast and reliable PDF text extraction")

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
                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True, hide_index=True)
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
