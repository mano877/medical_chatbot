from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks

from app.database.schemas import DocumentListResponse, DocumentOut, DocumentUploadResponse
from app.services.rag_service import start_pdf_ingestion, list_documents, delete_document
from app.utils.security import get_current_user

import os
import uuid

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user),
):
    """Upload a PDF medical document for Dr. Aria to reference."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)

    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)

    # Note: temp_path is NOT deleted here. The background task needs it.
    # It will clean up the file itself once processing is done.
    result = start_pdf_ingestion(temp_path, file.filename, current_user_id, background_tasks)

    return DocumentUploadResponse(
        doc_id=result["doc_id"],
        filename=result["filename"],
        chunks=0,
        message=result["message"],
    )


@router.get("", response_model=DocumentListResponse)
def list_all_documents(current_user_id: int = Depends(get_current_user)):
    """List documents uploaded by the logged-in user."""
    docs = list_documents(current_user_id)
    return DocumentListResponse(total=len(docs), documents=[DocumentOut(**doc) for doc in docs])


@router.delete("/{doc_id}")
def delete_document_route(doc_id: str, current_user_id: int = Depends(get_current_user)):
    """Delete your own document."""
    deleted = delete_document(doc_id, current_user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document with id '{doc_id}' not found.")
    return {"message": "Document and all its vector embeddings deleted successfully.", "doc_id": doc_id}