from sqlalchemy.orm import Session
from app.db.models import Document, Chunk
from app.models.document import DocumentCreate
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService


def create_document(db: Session, document_in: DocumentCreate) -> Document:
    document = Document(
        name=document_in.name,
        content=document_in.content,
        format=document_in.format,
        source_type=document_in.source_type,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        index_document(db, document.id)
    except Exception as exc:
        print(f"Document indexing failed for {document.id}: {exc}")

    return document


def index_document(db: Session, doc_id: int):
    """Chunk, embed, and index document."""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        return

    chunks = ChunkingService.chunk_text(document.content)
    if not chunks:
        return

    embeddings = EmbeddingService.embed_batch(chunks)

    metadata_list = [
        {
            "document_id": doc_id,
            "document_name": document.name,
            "chunk_index": i,
            "source_type": document.source_type or "unknown"
        }
        for i in range(len(chunks))
    ]

    VectorStoreService.add_chunks(doc_id, chunks, embeddings, metadata_list)

    for i, chunk_text in enumerate(chunks):
        db_chunk = Chunk(
            document_id=doc_id,
            chunk_text=chunk_text,
            chunk_index=i,
            vector_id=f"doc_{doc_id}_chunk_{i}"
        )
        db.add(db_chunk)

    db.commit()


def get_documents(db: Session):
    return db.query(Document).order_by(Document.created_at.desc()).all()


def get_chunk_count(db: Session, doc_id: int) -> int:
    """Get chunk count for a document."""
    return db.query(Chunk).filter(Chunk.document_id == doc_id).count()


def get_document_chunks(db: Session, doc_id: int):
    """Get all chunks for a document."""
    return db.query(Chunk).filter(Chunk.document_id == doc_id).order_by(Chunk.chunk_index).all()
