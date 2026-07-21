from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.document import DocumentCreate, DocumentResponse
from app.services.document_service import (
    create_document,
    get_documents,
    get_chunk_count,
    get_document_chunks,
)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/documents/upload-text", response_model=DocumentResponse)
def upload_document_text(document: DocumentCreate, db: Session = Depends(get_db)):
    if not document.content.strip():
        raise HTTPException(status_code=400, detail="Document content cannot be empty.")
    return create_document(db, document)


@router.post("/documents/upload-file", response_model=DocumentResponse)
async def upload_document_file(
    name: str = Form(...),
    format: str = Form(...),
    source_type: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = (await file.read()).decode("utf-8")

    if not content.strip():
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    document_in = DocumentCreate(
        name=name,
        content=content,
        format=format,
        source_type=source_type,
    )

    return create_document(db, document_in)


@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    return get_documents(db)


@router.get("/documents/{doc_id}/chunks-count")
def get_doc_chunk_count(doc_id: int, db: Session = Depends(get_db)):
    """Get chunk count for a document."""
    count = get_chunk_count(db, doc_id)
    return {"chunk_count": count}
