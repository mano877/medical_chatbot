"""
RAG Service manages PDF document ingestion, vector storage (Pinecone),
and context retrieval for Dr. Aria using HYBRID SEARCH
(Vector Search + BM25 Keyword Search combined via RRF).

PDF processing (embedding + upserting) runs as a BACKGROUND TASK since
embedding many chunks can take 60-90+ seconds. The user gets an instant
response while the document status updates from "processing" to "ready".
"""

import os
import time
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document as LCDocument
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
from rank_bm25 import BM25Okapi

from app.database.database import Document, SessionLocal, settings

# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────
OLLAMA_BASE_URL  = settings.ollama_base_url
EMBEDDING_MODEL  = "qwen3-embedding:latest"

embeddings = OllamaEmbeddings(base_url=OLLAMA_BASE_URL, model=EMBEDDING_MODEL)

_pc = Pinecone(api_key=settings.pinecone_api_key)


def _get_index():
    existing = [idx.name for idx in _pc.list_indexes()]
    if settings.pinecone_index_name not in existing:
        _pc.create_index(
            name=settings.pinecone_index_name,
            dimension=4096,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=settings.pinecone_environment),
        )
    return _pc.Index(settings.pinecone_index_name)


index = _get_index()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ".", " ", ""],
)


# ─────────────────────────────────────────────
#  BM25 + RRF
# ─────────────────────────────────────────────

def _bm25_search(query: str, docs: list[LCDocument], k: int = 5) -> list[LCDocument]:
    if not docs:
        return []
    tokenized_docs = [doc.page_content.lower().split() for doc in docs]
    tokenized_query = query.lower().split()
    bm25 = BM25Okapi(tokenized_docs)
    scores = bm25.get_scores(tokenized_query)
    scored_docs = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    return [doc for score, doc in scored_docs[:k] if score > 0]


def _reciprocal_rank_fusion(vector_results, keyword_results, k: int = 60):
    scores: dict[str, float] = {}
    doc_map: dict[str, LCDocument] = {}
    for rank, doc in enumerate(vector_results):
        doc_id = doc.page_content[:100]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
        doc_map[doc_id] = doc
    for rank, doc in enumerate(keyword_results):
        doc_id = doc.page_content[:100]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
        doc_map[doc_id] = doc
    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [doc_map[doc_id] for doc_id in sorted_ids]


def _vector_search(query: str, user_id: int, k: int) -> list[LCDocument]:
    query_vector = embeddings.embed_query(query)
    results = index.query(
        vector=query_vector, top_k=k, include_metadata=True,
        filter={"user_id": user_id},
    )
    docs = []
    for match in results.matches:
        if match.metadata and "text" in match.metadata:
            docs.append(LCDocument(
                page_content=match.metadata["text"],
                metadata={
                    "doc_id": match.metadata.get("doc_id"),
                    "filename": match.metadata.get("filename"),
                    "user_id": match.metadata.get("user_id"),
                },
            ))
    return docs


# ─────────────────────────────────────────────
#  Background Processing
# ─────────────────────────────────────────────

def _process_pdf_background(file_path: str, filename: str, user_id: int, doc_record_id: int):
    """
    Runs in the background AFTER the user already got a response.
    Does the slow embedding work, then updates status to 'ready' (or 'failed').
    Cleans up the temp file when done, success or failure.
    """
    t0 = time.time()
    try:
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        chunks = text_splitter.split_documents(pages)

        texts = [chunk.page_content for chunk in chunks]
        vecs = embeddings.embed_documents(texts)
        print(f"DEBUG: embedding took {time.time()-t0:.1f}s for {len(chunks)} chunks")

        db = SessionLocal()
        try:
            doc_record = db.query(Document).filter(Document.id == doc_record_id).first()
            doc_id = str(doc_record.id)

            vectors = []
            for i, (chunk, vec) in enumerate(zip(chunks, vecs)):
                vectors.append({
                    "id": f"{doc_id}_chunk_{i}",
                    "values": vec,
                    "metadata": {
                        "text": chunk.page_content,
                        "doc_id": doc_id,
                        "filename": filename,
                        "user_id": user_id,
                    },
                })

            batch_size = 100
            for start in range(0, len(vectors), batch_size):
                index.upsert(vectors=vectors[start:start + batch_size])

            doc_record.chunks = len(chunks)
            doc_record.status = "ready"
            db.commit()
            print(f"DEBUG: document {doc_id} ready, total {time.time()-t0:.1f}s")
        finally:
            db.close()

    except Exception as e:
        print(f"ERROR: background PDF processing failed: {e}")
        db = SessionLocal()
        try:
            doc_record = db.query(Document).filter(Document.id == doc_record_id).first()
            if doc_record:
                doc_record.status = "failed"
                db.commit()
        finally:
            db.close()

    finally:
        # Clean up the temp file now that we're fully done with it
        if os.path.exists(file_path):
            os.remove(file_path)


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def start_pdf_ingestion(file_path: str, filename: str, user_id: int, background_tasks) -> dict:
    """
    Called by the router. Creates a Document record immediately with
    status='processing', schedules the slow work in the background,
    and returns right away so the user isn't stuck waiting.
    """
    db = SessionLocal()
    try:
        doc_record = Document(
            doc_id="pending",
            filename=filename,
            chunks=0,
            status="processing",
            user_id=user_id,
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        doc_record.doc_id = str(doc_record.id)
        db.commit()

        doc_record_id = doc_record.id
        doc_id = doc_record.doc_id
    finally:
        db.close()

    background_tasks.add_task(
        _process_pdf_background, file_path, filename, user_id, doc_record_id
    )

    return {
        "doc_id": doc_id,
        "filename": filename,
        "status": "processing",
        "message": "Upload received. Your document is being processed. This may take a minute.",
    }


def get_document_status(doc_id: str, user_id: int) -> Optional[dict]:
    """Check the current status of a document."""
    db = SessionLocal()
    try:
        record = db.query(Document).filter(
            Document.doc_id == doc_id, Document.user_id == user_id
        ).first()
        if not record:
            return None
        return {
            "doc_id": record.doc_id,
            "filename": record.filename,
            "status": record.status,
            "chunks": record.chunks,
        }
    finally:
        db.close()


def list_documents(user_id: int) -> list[dict]:
    db = SessionLocal()
    try:
        docs = db.query(Document).filter(Document.user_id == user_id).all()
        return [
            {
                "doc_id": d.doc_id,
                "filename": d.filename,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                "chunks": d.chunks,
                "status": d.status,
                "user_id": d.user_id,
            }
            for d in docs
        ]
    finally:
        db.close()


def delete_document(doc_id: str, user_id: int) -> bool:
    db = SessionLocal()
    try:
        record = db.query(Document).filter(
            Document.doc_id == doc_id, Document.user_id == user_id
        ).first()
        if not record:
            return False
        index.delete(filter={"doc_id": doc_id, "user_id": user_id})
        db.delete(record)
        db.commit()
        return True
    finally:
        db.close()


def query_documents(query: str, user_id: int, k: int = 5) -> list[LCDocument]:
    vector_results = _vector_search(query, user_id, k=k * 2)
    keyword_results = _bm25_search(query, vector_results, k=k * 2)
    combined = _reciprocal_rank_fusion(vector_results, keyword_results) if keyword_results else vector_results
    return combined[:k]


def get_rag_context(query: str, user_id: int, k: int = 5) -> Optional[str]:
    """Only searches documents with status='ready' — skips ones still processing."""
    db = SessionLocal()
    try:
        has_ready_docs = db.query(Document).filter(
            Document.user_id == user_id, Document.status == "ready"
        ).first()
    finally:
        db.close()

    if not has_ready_docs:
        return None

    docs = query_documents(query, user_id, k=k)
    if not docs:
        return None

    sections = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("filename", "Unknown")
        sections.append(f"[Source {i}: {source}]\n{doc.page_content.strip()}")

    return "\n\n---\n\n".join(sections)