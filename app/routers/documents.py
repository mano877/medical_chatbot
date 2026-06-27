import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File

from app.database.schemas import DocumentListResponse, DocumentOut, DocumentUploadResponse
from app.services.rag_service import ingest_pdf, list_documents, delete_document

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"

# Ensure the temporary upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF medical document (lab report, prescription, health guideline, etc.)
    for Dr. Aria to reference during consultations.

    The PDF is parsed, split into chunks, embedded with ``nomic-embed-text``,
    and stored in the local ChromaDB vector store.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Save temporarily to disk so PyPDFLoader can read it
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        result = ingest_pdf(temp_path, file.filename)

        return DocumentUploadResponse(
            doc_id=result["doc_id"],
            filename=result["filename"],
            chunks=result["chunks"],
            message=(
                f"Document '{file.filename}' uploaded and ingested "
                f"successfully ({result['chunks']} text chunks indexed)."
            ),
        )
    finally:
        # Clean up the temp file regardless of success/failure
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("", response_model=DocumentListResponse)
def list_all_documents():
    """List all PDF documents that have been uploaded and indexed."""
    docs = list_documents()
    return DocumentListResponse(
        total=len(docs),
        documents=[DocumentOut(**doc) for doc in docs],
    )


@router.delete("/{doc_id}")
def delete_document_endpoint(doc_id: str):
    """Delete a previously uploaded document and all of its vector embeddings.

    The document is removed from both ChromaDB and the metadata tracker.
    """
    deleted = delete_document(doc_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Document with id '{doc_id}' not found.",
        )
    return {
        "message": "Document and all its vector embeddings deleted successfully.",
        "doc_id": doc_id,
    }
