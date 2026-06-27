"""
RAG Service — manages PDF document ingestion, vector storage (ChromaDB),
and context retrieval for Dr. Aria using HYBRID SEARCH
(Vector Search + BM25 Keyword Search combined via RRF).
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi

# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────
CHROMA_DB_DIR    = "chroma_db"
COLLECTION_NAME  = "medical_documents"
OLLAMA_BASE_URL  = "http://154.57.212.236:11434"
EMBEDDING_MODEL  = "qwen3-embedding:latest"
METADATA_FILE    = os.path.join(CHROMA_DB_DIR, "documents_metadata.json")

# ─────────────────────────────────────────────
#  Embeddings & Vector Store
# ─────────────────────────────────────────────
embeddings = OllamaEmbeddings(
    base_url=OLLAMA_BASE_URL,
    model=EMBEDDING_MODEL,
)

vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=CHROMA_DB_DIR,
)

# ─────────────────────────────────────────────
#  Text Splitter
# ─────────────────────────────────────────────
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ".", " ", ""],
)


# ─────────────────────────────────────────────
#  Metadata Helpers
# ─────────────────────────────────────────────

def _load_metadata() -> list[dict]:
    """Load document metadata from the JSON tracking file."""
    if not os.path.exists(METADATA_FILE):
        return []
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError, OSError):
        return []


def _save_metadata(metadata: list[dict]) -> None:
    """Save document metadata to the JSON tracking file."""
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)


# ─────────────────────────────────────────────
#  BM25 Keyword Search
# ─────────────────────────────────────────────

def _bm25_search(query: str, docs: list[Document], k: int = 5) -> list[Document]:
    """Keyword search using BM25 algorithm.
    
    Finds documents containing exact or similar words to the query.
    Think of it as a smart Ctrl+F search.
    """
    if not docs:
        return []

    # Tokenize all documents
    tokenized_docs = [doc.page_content.lower().split() for doc in docs]
    tokenized_query = query.lower().split()

    # Build BM25 index
    bm25 = BM25Okapi(tokenized_docs)

    # Get scores for each document
    scores = bm25.get_scores(tokenized_query)

    # Sort by score and return top k
    scored_docs = sorted(
        zip(scores, docs),
        key=lambda x: x[0],
        reverse=True
    )

    return [doc for score, doc in scored_docs[:k] if score > 0]


# ─────────────────────────────────────────────
#  RRF — Reciprocal Rank Fusion
# ─────────────────────────────────────────────

def _reciprocal_rank_fusion(
    vector_results: list[Document],
    keyword_results: list[Document],
    k: int = 60,
) -> list[Document]:
    """Combine vector and keyword search results using RRF.
    
    RRF gives higher scores to documents that rank well in BOTH searches.
    This is what makes hybrid search better than either alone.
    
    Args:
        vector_results: Results from ChromaDB vector search
        keyword_results: Results from BM25 keyword search
        k: RRF constant (60 is standard)
    
    Returns:
        Combined and re-ranked list of documents
    """
    scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    # Score vector search results
    for rank, doc in enumerate(vector_results):
        doc_id = doc.page_content[:100]  # use content as unique key
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
        doc_map[doc_id] = doc

    # Score keyword search results
    for rank, doc in enumerate(keyword_results):
        doc_id = doc.page_content[:100]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
        doc_map[doc_id] = doc

    # Sort by combined RRF score
    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [doc_map[doc_id] for doc_id in sorted_ids]


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def ingest_pdf(file_path: str, filename: str) -> dict:
    """Load a PDF, split into chunks, embed, and store in ChromaDB."""
    doc_id = str(uuid.uuid4())

    loader = PyPDFLoader(file_path)
    pages = loader.load()

    for page in pages:
        page.metadata["doc_id"] = doc_id
        page.metadata["filename"] = filename

    chunks = text_splitter.split_documents(pages)
    vector_store.add_documents(chunks)

    meta = _load_metadata()
    meta.append({
        "doc_id": doc_id,
        "filename": filename,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "chunks": len(chunks),
    })
    _save_metadata(meta)

    return {"doc_id": doc_id, "filename": filename, "chunks": len(chunks)}


def list_documents() -> list[dict]:
    """Return a list of all uploaded documents with their metadata."""
    return _load_metadata()


def delete_document(doc_id: str) -> bool:
    """Delete all vector chunks belonging to a document from ChromaDB."""
    meta = _load_metadata()
    found = any(m["doc_id"] == doc_id for m in meta)
    if not found:
        return False

    vector_store.delete(where={"doc_id": doc_id})
    meta = [m for m in meta if m["doc_id"] != doc_id]
    _save_metadata(meta)
    return True


def query_documents(query: str, k: int = 5) -> list[Document]:
    """
    HYBRID SEARCH — combines Vector Search + BM25 Keyword Search.
    
    Flow:
    1. Vector search  → finds semantically similar chunks (meaning-based)
    2. BM25 search    → finds exact keyword matches (word-based)
    3. RRF fusion     → combines and re-ranks both results
    4. Returns best combined results
    """
    # Step 1 — Vector search (semantic similarity)
    vector_results = vector_store.similarity_search(query, k=k * 2)

    # Step 2 — BM25 keyword search on the same documents
    keyword_results = _bm25_search(query, vector_results, k=k * 2)

    # Step 3 — Combine with RRF
    if keyword_results:
        combined = _reciprocal_rank_fusion(vector_results, keyword_results)
    else:
        combined = vector_results

    # Step 4 — Return top k results
    return combined[:k]


def get_rag_context(query: str, k: int = 5) -> Optional[str]:
    """Retrieve relevant document context using HYBRID SEARCH.

    Returns None if no documents uploaded yet.
    """
    meta = _load_metadata()
    if not meta:
        return None

    docs = query_documents(query, k=k)
    if not docs:
        return None

    sections = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("filename", "Unknown")
        sections.append(
            f"[Source {i}: {source}]\n{doc.page_content.strip()}"
        )

    return "\n\n---\n\n".join(sections)